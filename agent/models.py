from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str


class Post(BaseModel):
    title: str
    slug: str = Field(description="lowercase-kebab-case, no date")
    summary: str = Field(description="One or two sentences for the index page and RSS")
    tags: list[str]
    body_markdown: str = Field(description="The full post in Markdown, no H1 title")
    sources: list[Source]


class Criterion(BaseModel):
    name: str
    score: int = Field(description="1 (poor) to 5 (excellent)")
    note: str


class Review(BaseModel):
    criteria: list[Criterion]
    unsupported_claims: list[str] = Field(description="Claims in the post not backed by the research notes")
    overall: float = Field(description="Mean of criterion scores, 1-5")
    revision_instructions: str


class Proposal(BaseModel):
    reasoning: str = Field(description="Patterns observed across the issues and why each change should help")
    new_playbook: str = Field(description="The complete revised playbook.md")
    sources_to_add: list[str] = Field(description="RSS/Atom feed URLs to add")
    sources_to_remove: list[str] = Field(description="Feed URLs to drop (low quality or dead)")
    lesson: str = Field(description="One-paragraph lesson to append to memory/lessons.md")
