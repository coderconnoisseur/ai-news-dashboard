"""
AI Service: OpenRouter-powered summarization, impact scoring, and broadcast caption generation.
"""
import logging
import os
from typing import List, Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: Optional[httpx.Client] = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0,
        )
    return _client


def _get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")


def _get_openrouter_model() -> str:
    model = os.getenv("OPENROUTER_MODEL") or getattr(settings, "OPENROUTER_MODEL", "")
    return model or "openai/gpt-4o-mini"


def _extract_content(response_json: dict) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content", "")

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


def _complete(prompt: str, max_tokens: int, temperature: float = 0.2) -> str:
    api_key = _get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    payload = {
        "model": _get_openrouter_model(),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    client = get_client()
    response = client.post(
        "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "AI News Dashboard",
        },
        json=payload,
    )
    response.raise_for_status()
    return _extract_content(response.json())


def summarize_article(title: str, raw_summary: str) -> str:
    """
    Generate a clean 2-3 sentence AI summary of a news item.
    """
    try:
        result = _complete(
            prompt=(
                f"Summarize this AI news item in 2-3 concise sentences. "
                f"Be factual and highlight the key development.\n\n"
                f"Title: {title}\n"
                f"Content: {raw_summary[:800]}\n\n"
                f"Summary:"
            ),
            max_tokens=200,
        )
        return result
    except Exception as e:
        logger.warning(f"AI summarization failed: {e}")
        return raw_summary[:300] if raw_summary else ""


def score_impact(title: str, summary: str) -> float:
    """
    Score the impact/importance of a news item from 0-10.
    Returns 5.0 as fallback.
    """
    try:
        result = _complete(
            prompt=(
                f"Rate the impact/importance of this AI news item from 0 to 10. "
                f"Reply with ONLY the number (e.g. 7.5).\n\n"
                f"Title: {title}\n"
                f"Summary: {summary[:400]}"
            ),
            max_tokens=10,
            temperature=0.0,
        )
        return float(result)
    except Exception as e:
        logger.warning(f"Impact scoring failed: {e}")
        return 5.0


def generate_linkedin_post(news_items: List[dict]) -> str:
    """
    Generate a LinkedIn post for a list of favorited news items.
    """
    items_text = "\n".join(
        f"- {item['title']} ({item.get('source_name', 'AI News')})"
        for item in news_items[:5]
    )
    try:
        result = _complete(
            prompt=(
                f"Write a professional LinkedIn post sharing these top AI news items. "
                f"Use an engaging hook, bullet points, and 3-5 relevant hashtags. "
                f"Keep it under 300 words.\n\n"
                f"News items:\n{items_text}"
            ),
            max_tokens=400,
        )
        return result
    except Exception as e:
        logger.warning(f"LinkedIn caption generation failed: {e}")
        return f"Today's top AI news:\n\n{items_text}\n\n#AI #MachineLearning #Tech"


def generate_newsletter_content(news_items: List[dict]) -> str:
    """
    Generate newsletter HTML snippet for selected items.
    """
    items_text = "\n".join(
        f"- {item['title']}: {item.get('summary', '')[:200]}"
        for item in news_items[:10]
    )
    try:
        result = _complete(
            prompt=(
                f"Write a concise AI newsletter section covering these stories. "
                f"Include a brief intro paragraph and organized summaries. "
                f"Format with HTML (h2, p, ul tags only).\n\n"
                f"Stories:\n{items_text}"
            ),
            max_tokens=800,
        )
        return result
    except Exception as e:
        logger.warning(f"Newsletter generation failed: {e}")
        return f"<h2>This Week in AI</h2><ul>" + \
               "".join(f"<li>{i['title']}</li>" for i in news_items) + "</ul>"


def generate_email_body(news_items: List[dict]) -> str:
    """Generate plain-text email body for broadcast."""
    lines = ["Here are your curated AI news highlights:\n"]
    for item in news_items:
        lines.append(f"📰 {item['title']}")
        if item.get("summary"):
            lines.append(f"   {item['summary'][:200]}")
        lines.append(f"   🔗 {item['url']}\n")
    return "\n".join(lines)