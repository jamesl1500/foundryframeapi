"""Google Lighthouse metrics via the PageSpeed Insights API.

Running headless Chrome ourselves is heavy to operate on AWS; PageSpeed Insights
runs the same Lighthouse engine on Google's infrastructure and hands back the
full report as JSON, so we just call it and pull out the parts we care about.
"""
from typing import Any

import httpx

from api.core.config import get_api_settings

settings = get_api_settings()

PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]

# Lighthouse audit id -> friendly metric name
_METRIC_AUDITS = {
    "first-contentful-paint": "first_contentful_paint",
    "largest-contentful-paint": "largest_contentful_paint",
    "total-blocking-time": "total_blocking_time",
    "cumulative-layout-shift": "cumulative_layout_shift",
    "speed-index": "speed_index",
    "interactive": "time_to_interactive",
}


class LighthouseError(Exception):
    """Raised when the PageSpeed Insights API call fails or returns no report."""


async def run_lighthouse(url: str, strategy: str | None = None) -> dict[str, Any]:
    """Fetch Lighthouse scores + Core Web Vitals for `url` via PageSpeed Insights."""
    params: dict[str, Any] = {
        "url": url,
        "strategy": strategy or settings.lighthouse_strategy,
        "category": CATEGORIES,
    }
    if settings.pagespeed_api_key:
        params["key"] = settings.pagespeed_api_key

    try:
        async with httpx.AsyncClient(timeout=settings.lighthouse_timeout_seconds) as client:
            response = await client.get(PAGESPEED_ENDPOINT, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LighthouseError(f"PageSpeed Insights request failed: {exc}") from exc

    lighthouse_result = response.json().get("lighthouseResult")
    if not lighthouse_result:
        raise LighthouseError("PageSpeed Insights returned no Lighthouse result")

    categories = lighthouse_result.get("categories", {})
    audits = lighthouse_result.get("audits", {})

    scores = {
        name.replace("-", "_"): round((category.get("score") or 0) * 100, 1)
        for name, category in categories.items()
    }

    return {
        "strategy": strategy or settings.lighthouse_strategy,
        "scores": scores,
        "metrics": _extract_metrics(audits),
        "opportunities": _extract_opportunities(audits),
    }


def _extract_metrics(audits: dict) -> dict:
    metrics = {}
    for audit_id, name in _METRIC_AUDITS.items():
        audit = audits.get(audit_id)
        if audit:
            metrics[name] = {
                "value": audit.get("numericValue"),
                "unit": audit.get("numericUnit"),
                "display_value": audit.get("displayValue"),
                "score": audit.get("score"),
            }
    return metrics


def _extract_opportunities(audits: dict, limit: int = 8) -> list[dict]:
    """Failed/low-scoring audits, sorted worst-first, for the AI + report to surface."""
    opportunities = [
        {
            "id": audit_id,
            "title": audit.get("title"),
            "description": audit.get("description"),
            "score": audit.get("score"),
            "display_value": audit.get("displayValue"),
        }
        for audit_id, audit in audits.items()
        if audit.get("score") is not None and audit["score"] < 0.9
    ]
    opportunities.sort(key=lambda a: a["score"])
    return opportunities[:limit]
