"""Deterministic helpers for the keyless routine (no Claude API calls here).

  python -m agent.cli gather                 # fresh feed items as JSON (stdout)
  python -m agent.cli recent                 # recent post files, to avoid repeats
  python -m agent.cli finalize POST REVIEW [--strip]
                                             # enforce the publish gate, write metrics;
                                             # --strip deletes sentences with flagged claims
  python -m agent.cli reject DATE REVIEW     # record a day that failed the gate
  python -m agent.cli learn-due              # exit 0 if a learning cycle is due
  python -m agent.cli learn-signals          # signals for the learning cycle as YAML
  python -m agent.cli learn-check OLD NEW    # enforce the playbook change cap
  python -m agent.cli learn-record RESULT    # write learn metrics + state
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
import difflib
import json
import pathlib
import subprocess
import sys
import time

import feedparser
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIN_SCORE = 4.0
WINDOW_HOURS = 36
BATCH = 4
MAX_CHANGE = 0.35
BOT_AUTHORS = {"github-actions[bot]", "Claude"}


def rj(rel, default):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def wj(rel, data):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def die(msg):
    print(f"GATE FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def gather():
    covered = set(rj("memory/covered.json", []))
    cutoff = time.time() - WINDOW_HOURS * 3600
    feeds = yaml.safe_load((ROOT / "sources.yaml").read_text())["feeds"]
    items, health = [], {}
    for f in feeds:
        try:
            parsed = feedparser.parse(f["url"], agent="ai-news-blog/1.0")
            fresh = 0
            for e in parsed.entries[:30]:
                ts = e.get("published_parsed") or e.get("updated_parsed")
                link = e.get("link", "")
                if (ts and calendar.timegm(ts) < cutoff) or not link or link in covered:
                    continue
                fresh += 1
                items.append({"feed": f["name"], "quality": f.get("quality", 3), "title": e.get("title", ""),
                              "url": link, "summary": (e.get("summary", "") or "")[:400]})
            health[f["url"]] = {"ok": bool(parsed.entries), "fresh": fresh}
        except Exception as exc:
            health[f["url"]] = {"ok": False, "fresh": 0, "error": str(exc)[:200]}
    items.sort(key=lambda i: -i["quality"])
    wj(".routine/feed_health.json", health)
    print(json.dumps(items[:60], indent=1, ensure_ascii=False))


def recent():
    for p in sorted((ROOT / "content/posts").glob("*.md"))[-14:]:
        print(p.stem)


def _review(path):
    r = json.loads(pathlib.Path(path).read_text())
    scores = [c["score"] for c in r["criteria"]]
    if len(scores) < 6:
        die("review must score all 6 rubric criteria")
    r["overall"] = round(sum(scores) / len(scores), 2)
    return r


def strip_claims(body, claims):
    """Delete each sentence (or list item) that contains a flagged claim. Returns (body, missing)."""
    missing = []
    for claim in claims:
        needle = claim.strip().strip('"\'').rstrip(".")
        idx = body.find(needle)
        if idx < 0:
            missing.append(claim)
            continue
        line_start = body.rfind("\n", 0, idx) + 1
        line_end = body.find("\n", idx)
        line_end = len(body) if line_end < 0 else line_end
        line = body[line_start:line_end]
        parts = re.split(r"(?<=[.!?])\s+", line)
        offset, kept = 0, []
        for part in parts:
            start = line.find(part, offset)
            offset = start + len(part)
            if not (start <= idx - line_start < offset):
                kept.append(part)
        new_line = " ".join(kept).strip()
        if re.fullmatch(r"(?:[-*]|\d+\.)\s*", new_line or "-"):
            new_line = ""
        body = body[:line_start] + new_line + body[line_end:]
    return re.sub(r"\n{3,}", "\n\n", body), missing


def finalize(post_path, review_path, *flags):
    post = pathlib.Path(post_path).resolve()
    raw = post.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        die("post must start with YAML front matter")
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front)
    for k in ("title", "date", "summary", "tags", "sources"):
        if not meta.get(k):
            die(f"front matter missing '{k}'")
    if not all(s.get("url", "").startswith("http") for s in meta["sources"]):
        die("every source needs an http(s) url")
    if not post.name.startswith(str(meta["date"])):
        die("file name must start with the post date")
    r = _review(review_path)
    if r.get("unsupported_claims") and "--strip" in flags:
        body, missing = strip_claims(body, r["unsupported_claims"])
        if missing:
            die(f"flagged claims not found verbatim in the post, cannot strip: {missing}")
        r["stripped_claims"], r["unsupported_claims"] = r["unsupported_claims"], []
        print(f"stripped {len(r['stripped_claims'])} flagged claim(s)")
    if r.get("unsupported_claims"):
        die(f"unsupported claims remain: {r['unsupported_claims']}")
    if r["overall"] < MIN_SCORE:
        die(f"score {r['overall']} < {MIN_SCORE}")
    meta["score"] = r["overall"]
    post.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---" + body, encoding="utf-8")
    date = str(meta["date"])
    reviews = rj(".routine/reviews.json", []) + [r]
    wj(f"metrics/{date}.json", {"date": date, "published": True, "title": meta["title"], "final_score": r["overall"],
                                "path": str(post.relative_to(ROOT)), "reviews": reviews,
                                "feed_health": rj(".routine/feed_health.json", {})})
    covered = rj("memory/covered.json", []) + [s["url"] for s in meta["sources"]]
    wj("memory/covered.json", sorted(set(covered))[-5000:])
    print(f"OK: published {post.relative_to(ROOT)} with score {r['overall']}")


def reject(date, review_path):
    r = _review(review_path)
    wj(f"metrics/{date}.json", {"date": date, "published": False, "final_score": r["overall"],
                                "reviews": rj(".routine/reviews.json", []) + [r],
                                "feed_health": rj(".routine/feed_health.json", {})})
    print(f"recorded unpublished day {date}")


def _new_metrics():
    last = rj("memory/learn_state.json", {"last_date": "1970-01-01"})["last_date"]
    ms = [rj(f"metrics/{p.name}", {}) for p in sorted((ROOT / "metrics").glob("20*.json"))]
    return last, [m for m in ms if m.get("date", "") > last]


def learn_due():
    _, new = _new_metrics()
    print(f"{len(new)} new issues since last cycle (need {BATCH})")
    sys.exit(0 if len(new) >= BATCH else 1)


def learn_signals():
    last, new = _new_metrics()
    out = subprocess.run(["git", "log", f"--since={last}", "--format=%H%x09%an", "--",
                          "content/posts", "playbook.md", "sources.yaml"], cwd=ROOT, capture_output=True, text=True).stdout
    edits = []
    for line in out.splitlines():
        sha, author = line.split("\t", 1)
        if author not in BOT_AUTHORS:
            edits.append(subprocess.run(["git", "show", "-p", sha], cwd=ROOT, capture_output=True, text=True).stdout[:6000])
    signals = {
        "issues": [{"date": m["date"], "title": m.get("title"), "published": m.get("published"),
                    "final_score": m.get("final_score"), "revisions": len(m.get("reviews", [])) - 1,
                    "criteria": (m.get("reviews") or [{}])[-1].get("criteria")} for m in new],
        "feed_health": [m.get("feed_health", {}) for m in new],
        "audience": rj("metrics/audience.json", None),
        "human_edits": edits or "(none)",
        "replay_dates": [m["date"] for m in new if m.get("published")][-3:],
    }
    print(yaml.safe_dump(signals, sort_keys=False, allow_unicode=True))


def learn_check(old, new):
    a, b = pathlib.Path(old).read_text(), pathlib.Path(new).read_text()
    ratio = 1 - difflib.SequenceMatcher(None, a, b).ratio()
    if ratio > MAX_CHANGE:
        die(f"playbook change ratio {ratio:.2f} exceeds cap {MAX_CHANGE}")
    print(f"OK: change ratio {ratio:.3f}")


def learn_record(result_path):
    result = json.loads(pathlib.Path(result_path).read_text())
    _, new = _new_metrics()
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    wj(f"metrics/learn-{today}.json", result)
    wj("memory/learn_state.json", {"last_date": max([m["date"] for m in new] or [today])})
    print("recorded learning cycle")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["help"]
    fn = {"gather": gather, "recent": recent, "finalize": finalize, "reject": reject, "learn-due": learn_due,
          "learn-signals": learn_signals, "learn-check": learn_check, "learn-record": learn_record}.get(cmd)
    if fn is None:
        print(__doc__)
        sys.exit(2)
    fn(*args)
