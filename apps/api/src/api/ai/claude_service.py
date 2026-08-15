"""Claude (Anthropic) integration: turns raw audit findings into a lead-facing
summary plus a recommended service package.
"""
import json

from anthropic import AsyncAnthropic

from api.core.config import get_api_settings
from api.services.audit_service import AuditReport

settings = get_api_settings()

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are a website audit analyst for a web agency. Given a JSON \
report of automated checks (including Google Lighthouse scores, Core Web Vitals, \
and Lighthouse improvement opportunities), respond with a JSON object (no markdown \
fences) containing exactly these keys:
- "summary": a 2-4 sentence, non-technical summary of the site's health.
- "priority_issues": an array of up to 5 short strings naming the most impactful issues.
- "recommended_package": one of "starter", "growth", "enterprise" based on issue severity/volume.
- "package_reason": one short sentence explaining the recommendation.
"""


async def generate_recommendations(report: AuditReport, url: str) -> dict:
    """Ask Claude to summarize findings and recommend a package for the lead."""
    payload = {
        "url": url,
        "overall_score": report.overall_score,
        "category_scores": report.category_scores,
        "findings": [f.__dict__ for f in report.findings],
        "lighthouse_metrics": report.lighthouse_metrics,
        "lighthouse_opportunities": report.lighthouse_opportunities,
    }

    client = _get_client()
    message = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )

    text = "".join(block.text for block in message.content if block.type == "text")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": text.strip(),
            "priority_issues": [],
            "recommended_package": "growth",
            "package_reason": "Unable to parse structured recommendation.",
        }
