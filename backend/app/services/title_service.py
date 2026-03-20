"""
Title polishing service.

Two-stage pipeline:
  Stage 1 — Regex cleaning  (fast, free, runs on every item)
    • Strips leading date prefixes:  "Feb 27, 2026Announcements..." → "..."
    • Strips leading category labels: "AnnouncementsStatement on..." → "Statement on..."
    • Collapses excess whitespace / punctuation artefacts
    • Trims arXiv boilerplate:  "[Submitted on 3 Mar 2026] Title" → "Title"

  Stage 2 — LLM polishing    (optional, Claude Haiku, batched)
    • Rewrites academic / awkward titles into clean, readable headlines
    • Only runs when POLISH_TITLES=true in config and the title passes a
      "needs polish" heuristic (too long, contains jargon brackets, etc.)

The two stages are deliberately decoupled so you can run Stage 1 alone
during ingestion (zero latency) and Stage 2 as a background enrichment
pass (like image enrichment).
"""
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models import NewsItem

logger = logging.getLogger(__name__)

# ─── Stage 1: regex patterns ──────────────────────────────────────────────────

# Month names used in date prefixes
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|"
    "October|November|December|"
    "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
)

# Patterns applied in order; first match wins per pattern (applied cumulatively)
_CLEAN_PATTERNS: list[tuple[str, str]] = [

    # "Feb 27, 2026AnnouncementsTitle" — date immediately followed by category+title
    (rf"^(?:{_MONTHS})\s+\d{{1,2}},?\s*\d{{4}}\s*", ""),

    # "2026-03-19 Title" or "19/03/2026 Title" — ISO / numeric date prefix
    (r"^\d{4}[-/]\d{2}[-/]\d{2}\s+", ""),
    (r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+", ""),

    # "AnnouncementsTitle" — capitalised category slug concatenated with title
    # Matches known Anthropic/OpenAI/etc. category labels with no space separator
    (
        r"^(Announcements|Research|News|Blog|Product|Policy|Safety|"
        r"Company|Updates?|Release|Launches?|Features?|Guide|Tutorial|"
        r"Interview|Podcast|Report|Analysis|Opinion|Commentary)"
        r"(?=[A-Z])",   # must be immediately followed by next capital (no space = scraper artefact)
        "",
    ),

    # arXiv: "[Submitted on 3 Mar 2026 (v1)]" prefix or trailing "(arXiv:...)"
    (r"^\[Submitted on [^\]]+\]\s*", ""),
    (r"\s*\(arXiv:[^)]+\)\s*$", ""),

    # arXiv abstract titles that start with "Title: "
    (r"^Title:\s*", ""),

    # Trailing " - Source Name" that some RSS feeds append
    (r"\s+[-–—]\s+(TechCrunch|VentureBeat|Wired|MIT Technology Review|"
     r"The Verge|Hacker News|ArXiv|arXiv)\s*$", ""),

    # Collapse multiple spaces / leading-trailing whitespace
    (r"\s{2,}", " "),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _CLEAN_PATTERNS]


def clean_title(raw: str) -> str:
    """
    Stage 1: apply all regex patterns in sequence and return a cleaned title.
    Safe to call on every item — purely deterministic, no I/O.
    """
    title = raw.strip()
    for pattern, replacement in _COMPILED:
        title = pattern.sub(replacement, title).strip()
    return title or raw.strip()   # never return empty string


def _needs_llm_polish(title: str) -> bool:
    """
    Heuristic: decide whether a title is messy enough to warrant LLM rewriting.
    Keeps LLM usage to a minimum — most titles are fine after Stage 1.
    """
    # Very long titles (arXiv academic papers)
    if len(title) > 120:
        return True
    # Contains bracketed noise e.g. "[1/2]", "(v2)", "[ICLR 2025]"
    if re.search(r"\[.{2,30}\]|\(.{2,20}\)", title):
        return True
    # Starts with a number (leftover artefact)
    if re.match(r"^\d+[\.\)]\s", title):
        return True
    # Contains a colon-separated academic structure "X: A study of Y using Z"
    if title.count(":") >= 2:
        return True
    return False


# ─── Stage 2: LLM polishing ───────────────────────────────────────────────────

_LLM_SYSTEM = (
    "You are a headline editor for an AI news dashboard. "
    "Rewrite each title into a clean, concise news headline (max 15 words). "
    "Rules:\n"
    "- Remove paper-style subtitles after colons unless essential\n"
    "- Remove method acronyms in parentheses e.g. '(RAG)', '(LoRA)' if already in title\n"
    "- Keep proper nouns, model names, and version numbers intact\n"
    "- Use sentence case (only first word and proper nouns capitalised)\n"
    "- Return ONLY the rewritten title, no explanation, no quotes\n"
)


def polish_title_with_llm(title: str) -> str:
    """
    Stage 2: use Claude Haiku to rewrite a messy title.
    Returns original title on any failure (never raises).
    """
    try:
        import anthropic
        from app.config import get_settings
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return title

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            system=_LLM_SYSTEM,
            messages=[{"role": "user", "content": title}],
        )
        polished = msg.content[0].text.strip().strip('"').strip("'")
        if polished and 5 < len(polished) < 300:
            return polished
    except Exception as e:
        logger.debug(f"LLM title polish failed: {e}")
    return title


def process_title(raw: str, use_llm: bool = False) -> str:
    """
    Full two-stage pipeline.
    use_llm=False  → Stage 1 only (ingestion path, zero latency)
    use_llm=True   → Stage 1 + Stage 2 if heuristic fires (enrichment path)
    """
    cleaned = clean_title(raw)
    if use_llm and _needs_llm_polish(cleaned):
        return polish_title_with_llm(cleaned)
    return cleaned


# ─── Batch enrichment (background pass) ──────────────────────────────────────

MAX_POLISH_PER_CYCLE = 30   # cap LLM calls per fetch cycle


def enrich_titles(db: Session, use_llm: bool = True) -> int:
    """
    Find recently saved items whose titles still need polishing
    (identified by the needs_llm_polish heuristic) and rewrite them.
    Returns count of titles updated.
    """
    # Only query items that haven't been polished yet.
    # We reuse the ai_summary IS NULL check as a proxy since both enrichments
    # run together — items get summaries at the same time as title polish.
    candidates = (
        db.query(NewsItem)
        .filter(NewsItem.ai_summary.is_(None))
        .order_by(NewsItem.fetched_at.desc())
        .limit(MAX_POLISH_PER_CYCLE * 3)   # fetch more, filter down
        .all()
    )

    updated = 0
    for item in candidates:
        if updated >= MAX_POLISH_PER_CYCLE:
            break

        original = item.title
        cleaned  = clean_title(original)

        # Always apply Stage 1
        if cleaned != original:
            item.title = cleaned
            updated += 1
            logger.debug(f"Title cleaned: {original!r} → {cleaned!r}")
            continue

        # Stage 2 only if heuristic fires and LLM enabled
        if use_llm and _needs_llm_polish(cleaned):
            polished = polish_title_with_llm(cleaned)
            if polished != cleaned:
                item.title = polished
                updated += 1
                logger.debug(f"Title polished: {cleaned!r} → {polished!r}")

    if updated:
        db.commit()
        logger.info(f"Title enrichment: {updated} titles updated")
    return updated