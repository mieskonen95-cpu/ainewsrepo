"""Learning loop: collect signals -> reflect -> propose -> eval gate -> update.

Runs after every BATCH new posts. The model stays fixed; playbook.md and sources.yaml learn.
rubric.md is never written by this script.

Run: python -m agent.learn [--force]
"""
from __future__ import annotations

import difflib
import statistics
import subprocess
import sys

import yaml

from .common import ROOT, log, read, read_json, structured, today, write, write_json
from .models import Proposal
from .produce import draft, judge

BATCH = 4                 # learn from at least this many new issues
MAX_CHANGE = 0.35         # cap: at most this share of the playbook may change per cycle
EVAL_DAYS = 3             # replay this many past days in the eval gate
BOT = "github-actions[bot]"


def human_edits(since: str) -> str:
    """Diffs that people (not the bot) committed to posts/playbook/sources since `since`."""
    out = subprocess.run(
        ["git", "log", f"--since={since}", "--format=%H%x09%an", "--", "content/posts", "playbook.md", "sources.yaml"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    diffs = []
    for line in out.splitlines():
        sha, author = line.split("\t", 1)
        if author == BOT:
            continue
        diffs.append(subprocess.run(["git", "show", "--stat", "-p", sha], cwd=ROOT, capture_output=True, text=True).stdout[:8000])
    return "\n\n".join(diffs) or "(no human edits)"


def change_ratio(old: str, new: str) -> float:
    return 1 - difflib.SequenceMatcher(None, old, new).ratio()


def eval_playbook(playbook: str, dates: list[str]) -> list[float]:
    lessons = read("memory/lessons.md")
    scores = []
    for d in dates:
        notes = read(f"memory/notes/{d}.md")
        review = judge(draft(playbook, lessons, notes), notes)
        scores.append(review.overall - 0.5 * len(review.unsupported_claims))
    return scores


def main() -> int:
    state = read_json("memory/learn_state.json", {"last_date": "1970-01-01"})
    metrics = [read_json(f"metrics/{p.name}", {}) for p in sorted((ROOT / "metrics").glob("20*.json"))]
    new = [m for m in metrics if m.get("date", "") > state["last_date"]]
    if len(new) < BATCH and "--force" not in sys.argv:
        log(f"{len(new)} new issues since last cycle; waiting for {BATCH}.")
        return 0

    old_playbook = read("playbook.md")
    sources = yaml.safe_load(read("sources.yaml"))
    signals = {
        "issues": [
            {k: m.get(k) for k in ("date", "title", "published", "final_score")}
            | {"criteria": m["reviews"][-1]["criteria"], "revisions": len(m["reviews"]) - 1}
            for m in new if m.get("reviews")
        ],
        "feed_health": [m.get("feed_health", {}) for m in new],
        "audience": read_json("metrics/audience.json", None),  # optional: drop analytics here
    }

    system = (
        "You improve the editorial playbook of an automated AI news blog. Look for patterns across "
        "several issues, not one-offs. Make small, targeted changes. Human edits are the strongest "
        "signal, then audience data, then rubric scores. Never optimise for clicks at the expense of "
        "accuracy. You cannot change the rubric."
    )
    user = f"""<playbook>
{old_playbook}
</playbook>

<sources>
{yaml.safe_dump(sources, sort_keys=False)}
</sources>

<rubric>
{read("rubric.md")}
</rubric>

<lessons_so_far>
{read("memory/lessons.md")}
</lessons_so_far>

<human_edits>
{human_edits(state["last_date"])}
</human_edits>

<signals>
{yaml.safe_dump(signals, sort_keys=False, allow_unicode=True)}
</signals>

Propose a revised playbook and source changes."""
    proposal = structured(Proposal, system, user, effort="xhigh")

    ratio = change_ratio(old_playbook, proposal.new_playbook)
    result = {"date": today(), "change_ratio": round(ratio, 3), "reasoning": proposal.reasoning}
    accepted = False
    if ratio > MAX_CHANGE:
        result["rejected"] = f"change ratio {ratio:.2f} exceeds cap {MAX_CHANGE}"
    else:
        dates = [m["date"] for m in new if m.get("published")][-EVAL_DAYS:] or [m["date"] for m in new][-EVAL_DAYS:]
        old_s, new_s = eval_playbook(old_playbook, dates), eval_playbook(proposal.new_playbook, dates)
        result |= {"eval_dates": dates, "old_scores": old_s, "new_scores": new_s}
        accepted = statistics.mean(new_s) >= statistics.mean(old_s) and min(new_s) >= min(old_s) - 0.5
        if not accepted:
            result["rejected"] = "eval gate: new playbook did not beat the old one on replayed days"

    if accepted:
        write("playbook.md", proposal.new_playbook.strip() + "\n")
        feeds = [f for f in sources["feeds"] if f["url"] not in set(proposal.sources_to_remove)]
        known = {f["url"] for f in feeds}
        feeds += [{"name": u.split("/")[2], "url": u, "quality": 3} for u in proposal.sources_to_add if u not in known]
        sources["feeds"] = feeds
        write("sources.yaml", yaml.safe_dump(sources, sort_keys=False, allow_unicode=True))
        result |= {"added": proposal.sources_to_add, "removed": proposal.sources_to_remove}
    # The lesson is kept either way: a rejected idea is also worth remembering.
    write("memory/lessons.md", read("memory/lessons.md").rstrip() + f"\n\n## {today()} ({'applied' if accepted else 'rejected'})\n{proposal.lesson}\n")

    result["accepted"] = accepted
    write_json(f"metrics/learn-{today()}.json", result)
    write_json("memory/learn_state.json", {"last_date": max(m["date"] for m in new) if new else today()})
    write(".learn-commit-msg", f"learn: {'update playbook' if accepted else 'proposal rejected'} ({today()})\n\n{proposal.reasoning[:3000]}\n")
    log("accepted" if accepted else f"rejected: {result.get('rejected')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
