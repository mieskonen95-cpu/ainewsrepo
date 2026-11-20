"""Shared helpers: Claude client, repo paths, file IO."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
from typing import TypeVar

import anthropic
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = os.environ.get("NEWS_MODEL", "claude-opus-5-5")
# Server-side fallback: if a request is declined, the API retries it on a suitable model.
BETAS = ["server-side-fallback-2026-07-01"]

client = anthropic.Anthropic(max_retries=4)
T = TypeVar("T", bound=BaseModel)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def read(rel: str, default: str = "") -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else default


def write(rel: str, text: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def read_json(rel: str, default):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write_json(rel: str, data) -> None:
    write(rel, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _check(resp) -> None:
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Model declined the request: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Response hit max_tokens; raise the limit.")


def structured(schema: type[T], system: str, user: str, effort: str = "high") -> T:
    """One call that returns a validated pydantic object."""
    resp = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        betas=BETAS,
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    _check(resp)
    return resp.parsed_output


def research(system: str, user: str, max_searches: int = 15) -> str:
    """Agentic web research with Anthropic's server-side web search; returns notes as text."""
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
    messages = [{"role": "user", "content": user}]
    for _ in range(8):
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=32000,
            betas=BETAS,
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=system,
            tools=tools,
            messages=messages,
        )
        if resp.stop_reason == "pause_turn":  # long server-tool turn: send it back to continue
            messages.append({"role": "assistant", "content": resp.content})
            continue
        _check(resp)
        return "\n".join(b.text for b in resp.content if b.type == "text").strip()
    raise RuntimeError("Research did not finish after repeated pause_turn continuations.")
