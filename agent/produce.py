"""Production loop: gather -> research -> draft -> self-critique vs rubric -> publish.

Run: python -m agent.produce [--force]
"""
from __future__ import annotations

import calendar
import sys
import time

import feedparser
import yaml

from .common import ROOT, log, read, read_json, research, structured, today, write, write_json
from .models import Post, Review

MIN_SCORE = 4.0       # publish bar on the fixed rubric (1-5)
MAX_REVISIONS = 2
WINDOW_HOURS = 36


def load_sources() -> list[dict]:
    return yaml.safe_load(read("sources.yaml"))["feeds"]


def gather() -> tuple[list[dict], dict]:
    covered = set(read_json("memory/covered.json", []))
    cutoff = time.time() - WINDOW_HOURS * 3600
    items, health = [], {}
    for feed in load_sources():
        try:
            parsed = feedparser.parse(feed["url"], agent="ai-news-blog/1.0")
            fresh = 0
            for e in parsed.entries[:30]:
                ts = e.get("published_parsed") or e.get("updated_parsed")
                if ts and calendar.timegm(ts) < cutoff:
                    continue
                link = e.get("link", "")
                if not link or link in covered:
                    continue
                fresh += 1
                items.append({
                    "feed": feed["name"],
                    "quality": feed.get("quality", 3),
                    "title": e.get("title", ""),
                    "url": link,
                    "summary": (e.get("summary", "") or "")[:500],
                })
            health[feed["url"]] = {"ok": not parsed.bozo or bool(parsed.entries), "fresh": fresh}
        except Exception as exc:  # one bad feed must not stop the run
            log(f"feed failed {feed['url']}: {exc}")
            health[feed["url"]] = {"ok": False, "fresh": 0}
    items.sort(key=lambda i: -i["quality"])
    return items[:60], health


def recent_titles(n: int = 14) -> list[str]:
    posts = sorted((ROOT / "content/posts").glob("*.md"))[-n:]
    return [p.stem for p in posts]


def do_research(items: list[dict], playbook: str) -> str:
    listing = "\n".join(f"- [{i['feed']} q{i['quality']}] {i['title']} — {i['url']}\n  {i['summary']}" for i in items)
    system = (
        "You are the research desk of an AI news blog. Pick the stories that matter most today "
        "according to the editorial playbook, verify them with web search, and find primary sources "
        "(papers, official announcements, repos). Write research notes, not the post."
    )
    user = f"""<playbook>
{playbook}
</playbook>

<recent_posts>
{chr(10).join(recent_titles()) or "(none yet)"}
</recent_posts>

<candidate_items>
{listing or "(feeds returned nothing new; find today's most important AI news with web search)"}
</candidate_items>

Choose the stories for today's post (follow the playbook's count) and avoid repeating recent posts.
For each story write: headline, what happened, why it matters, key facts and numbers, and the
source URLs that back each fact. Mark anything you could not verify as UNVERIFIED."""
    return research(system, user)


def draft(playbook: str, lessons: str, notes: str, feedback: str = "", previous: Post | None = None) -> Post:
    system = "You write posts for an AI news blog. Follow the playbook exactly. Use only facts in the research notes."
    user = f"<playbook>\n{playbook}\n</playbook>\n\n<lessons>\n{lessons}\n</lessons>\n\n<research_notes>\n{notes}\n</research_notes>\n\nDate: {today()}."
    if previous is not None:
        user += f"\n\n<previous_draft>\n{previous.model_dump_json()}\n</previous_draft>\n\n<editor_feedback>\n{feedback}\n</editor_feedback>\n\nRevise the draft to address every point."
    else:
        user += "\n\nWrite today's post."
    return structured(Post, system, user)


def judge(post: Post, notes: str) -> Review:
    rubric = read("rubric.md")
    system = (
        "You are a strict, independent editor. Score the post against the rubric. "
        "You did not write it. Flag every claim not supported by the research notes."
    )
    user = f"<rubric>\n{rubric}\n</rubric>\n\n<research_notes>\n{notes}\n</research_notes>\n\n<post>\n{post.model_dump_json()}\n</post>"
    return structured(Review, system, user)


def write_post(post: Post, review: Review, date: str) -> str:
    rel = f"content/posts/{date}-{post.slug}.md"
    front = {
        "title": post.title,
        "date": date,
        "summary": post.summary,
        "tags": post.tags,
        "score": round(review.overall, 2),
        "sources": [s.model_dump() for s in post.sources],
    }
    write(rel, "---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---\n\n" + post.body_markdown.strip() + "\n")
    return rel


def main() -> int:
    date = today()
    if any((ROOT / "content/posts").glob(f"{date}-*.md")) and "--force" not in sys.argv:
        log(f"Post for {date} already exists; skipping.")
        return 0

    playbook, lessons = read("playbook.md"), read("memory/lessons.md")
    items, health = gather()
    log(f"gathered {len(items)} candidate items")

    notes = do_research(items, playbook)
    write(f"memory/notes/{date}.md", notes)

    post = draft(playbook, lessons, notes)
    review = judge(post, notes)
    history = [review.model_dump()]
    for _ in range(MAX_REVISIONS):
        if review.overall >= MIN_SCORE and not review.unsupported_claims:
            break
        log(f"revising (score {review.overall:.2f}, {len(review.unsupported_claims)} unsupported claims)")
        feedback = review.revision_instructions + "\nRemove or fix: " + "; ".join(review.unsupported_claims)
        post = draft(playbook, lessons, notes, feedback, post)
        review = judge(post, notes)
        history.append(review.model_dump())

    published = review.overall >= MIN_SCORE and not review.unsupported_claims
    metrics = {
        "date": date,
        "published": published,
        "title": post.title,
        "final_score": review.overall,
        "reviews": history,
        "feed_health": health,
    }
    if published:
        metrics["path"] = write_post(post, review, date)
        covered = read_json("memory/covered.json", [])
        covered += [s.url for s in post.sources]
        write_json("memory/covered.json", sorted(set(covered))[-5000:])
        log(f"published {metrics['path']}")
    else:
        log(f"NOT published: score {review.overall:.2f} below bar or unsupported claims remain")
    write_json(f"metrics/{date}.json", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
