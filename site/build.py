"""Static site generator: content/posts/*.md -> _site/ (HTML + RSS). No framework needed.

Run: python site/build.py
"""
from __future__ import annotations

import html
import os
import pathlib
import shutil
from email.utils import format_datetime
from datetime import datetime, timezone

import markdown
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
SITE_TITLE = os.environ.get("SITE_TITLE", "The AI Brief")
SITE_TAGLINE = os.environ.get("SITE_TAGLINE", "AI news, researched and written by an agent that learns.")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")


def load_posts() -> list[dict]:
    posts = []
    for p in sorted((ROOT / "content/posts").glob("*.md"), reverse=True):
        raw = p.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front)
        meta["slug"] = p.stem
        meta["html"] = markdown.markdown(body, extensions=["extra", "sane_lists"])
        posts.append(meta)
    return posts


def page(title: str, body: str, depth: int) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><link rel="stylesheet" href="{up}style.css">
<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="{up}feed.xml"></head>
<body><header><a class="brand" href="{up}index.html">{html.escape(SITE_TITLE)}</a><a href="{up}feed.xml">RSS</a></header>
<main>{body}</main>
<footer>Written automatically by an AI agent from cited sources. Each post is scored against a fixed rubric before publishing.</footer>
</body></html>"""


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(ROOT / "site/style.css", OUT / "style.css")
    posts = load_posts()

    for p in posts:
        sources = "".join(f'<li><a href="{html.escape(s["url"])}">{html.escape(s["title"])}</a></li>' for s in p.get("sources", []))
        tags = " ".join(f"<span class=tag>{html.escape(t)}</span>" for t in p.get("tags", []))
        body = f"""<article><p class="meta">{p['date']} · {tags}</p><h1>{html.escape(p['title'])}</h1>
{p['html']}<h2>Sources</h2><ol class="sources">{sources}</ol></article>"""
        d = OUT / "posts" / p["slug"]
        d.mkdir()
        (d / "index.html").write_text(page(p["title"], body, 2), encoding="utf-8")

    items = "".join(
        f"""<li><p class="meta">{p['date']}</p><a href="posts/{p['slug']}/index.html"><h2>{html.escape(p['title'])}</h2></a>
<p>{html.escape(p.get('summary', ''))}</p></li>"""
        for p in posts
    ) or "<li><p>The first post is on its way.</p></li>"
    (OUT / "index.html").write_text(page(SITE_TITLE, f"<p class=tagline>{html.escape(SITE_TAGLINE)}</p><ul class=posts>{items}</ul>", 0), encoding="utf-8")

    rss_items = ""
    for p in posts[:30]:
        link = f"{SITE_URL}/posts/{p['slug']}/index.html"
        when = format_datetime(datetime.fromisoformat(str(p["date"])).replace(tzinfo=timezone.utc))
        rss_items += f"<item><title>{html.escape(p['title'])}</title><link>{link}</link><guid>{link}</guid><pubDate>{when}</pubDate><description>{html.escape(p.get('summary', ''))}</description></item>"
    (OUT / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{html.escape(SITE_TITLE)}</title>'
        f"<link>{SITE_URL}/</link><description>{html.escape(SITE_TAGLINE)}</description>{rss_items}</channel></rss>",
        encoding="utf-8",
    )
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(posts)} posts into {OUT}")


if __name__ == "__main__":
    build()
