"""Site auditor: fetches a page and runs a set of heuristic checks against it.

This is deliberately dependency-light (httpx + BeautifulSoup) so it runs fast
inside a request/response cycle. Results feed into the Claude AI layer, which
turns raw findings into a human-readable summary and package recommendation.
"""
import asyncio
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from api.core.config import get_api_settings
from api.services.lighthouse_service import LighthouseError, run_lighthouse

settings = get_api_settings()


@dataclass
class AuditFinding:
    category: str
    check: str
    passed: bool
    message: str
    weight: int = 1


@dataclass
class AuditReport:
    findings: list[AuditFinding] = field(default_factory=list)
    category_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    response_time_ms: float | None = None
    status_code: int | None = None
    lighthouse_scores: dict[str, float] | None = None
    lighthouse_metrics: dict | None = None
    lighthouse_opportunities: list[dict] | None = None
    lighthouse_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "findings": [f.__dict__ for f in self.findings],
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "lighthouse_metrics": self.lighthouse_metrics,
            "lighthouse_opportunities": self.lighthouse_opportunities,
            "lighthouse_error": self.lighthouse_error,
        }


class SiteAuditError(Exception):
    """Raised when a site cannot be fetched or audited."""


def _is_ssl_error(exc: BaseException) -> bool:
    """Walk an exception's cause/context chain looking for an underlying ssl.SSLError."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ssl.SSLError):
            return True
        current = current.__cause__ or current.__context__
    return False


async def run_audit(url: str) -> AuditReport:
    """Run the fast heuristic checks and Google Lighthouse (via PageSpeed Insights)
    concurrently, then merge Lighthouse's authoritative performance/accessibility/
    SEO/best-practices scores into the report.
    """
    report, lighthouse = await asyncio.gather(
        _run_heuristic_checks(url), _fetch_lighthouse(url)
    )

    scores, metrics, opportunities, error = lighthouse
    report.lighthouse_scores = scores
    report.lighthouse_metrics = metrics
    report.lighthouse_opportunities = opportunities
    report.lighthouse_error = error

    if scores:
        report.category_scores.update(scores)
        report.overall_score = round(
            sum(report.category_scores.values()) / len(report.category_scores), 1
        )

    return report


async def _fetch_lighthouse(
    url: str,
) -> tuple[dict[str, float] | None, dict | None, list[dict] | None, str | None]:
    try:
        result = await run_lighthouse(url)
    except LighthouseError as exc:
        return None, None, None, str(exc)
    return result["scores"], result["metrics"], result["opportunities"], None


async def _run_heuristic_checks(url: str) -> AuditReport:
    """Fetch `url` and run SEO / performance / accessibility / security checks."""
    headers = {"User-Agent": settings.audit_user_agent}
    start = time.perf_counter()

    tls_error: str | None = None
    fetch_url = url
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=settings.audit_request_timeout_seconds
        ) as client:
            response = await client.get(fetch_url, headers=headers)
    except httpx.HTTPError as exc:
        if fetch_url.startswith("https://") and _is_ssl_error(exc):
            # Some sites have broken/missing TLS termination; retry over plain HTTP so
            # the audit still runs and the TLS misconfiguration is surfaced as a finding.
            tls_error = str(exc)
            fetch_url = "http://" + fetch_url[len("https://") :]
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True, timeout=settings.audit_request_timeout_seconds
                ) as client:
                    response = await client.get(fetch_url, headers=headers)
            except httpx.HTTPError as fallback_exc:
                raise SiteAuditError(f"Failed to fetch {url}: {exc}") from fallback_exc
        else:
            raise SiteAuditError(f"Failed to fetch {url}: {exc}") from exc

    elapsed_ms = (time.perf_counter() - start) * 1000

    report = AuditReport(response_time_ms=round(elapsed_ms, 1), status_code=response.status_code)

    if tls_error:
        report.findings.append(
            AuditFinding(
                category="security",
                check="tls_handshake",
                passed=False,
                message=f"HTTPS handshake failed ({tls_error}); fell back to HTTP",
                weight=4,
            )
        )

    if response.status_code >= 400:
        report.findings.append(
            AuditFinding(
                category="availability",
                check="http_status",
                passed=False,
                message=f"Site responded with HTTP {response.status_code}",
                weight=5,
            )
        )
        _score(report)
        return report

    soup = BeautifulSoup(response.text, "lxml")
    parsed_url = urlparse(str(response.url))

    _check_https(report, parsed_url)
    _check_performance(report, elapsed_ms)
    _check_title(report, soup)
    _check_meta_description(report, soup)
    _check_headings(report, soup)
    _check_images_alt(report, soup)
    _check_viewport(report, soup)
    _check_canonical(report, soup, str(response.url))
    _check_security_headers(report, response.headers)
    await _check_robots_and_sitemap(report, str(response.url))

    _score(report)
    return report


def _score(report: AuditReport) -> None:
    """Aggregate findings into per-category and overall scores (0-100)."""
    categories: dict[str, list[AuditFinding]] = {}
    for finding in report.findings:
        categories.setdefault(finding.category, []).append(finding)

    for category, findings in categories.items():
        total_weight = sum(f.weight for f in findings)
        earned_weight = sum(f.weight for f in findings if f.passed)
        report.category_scores[category] = (
            round(100 * earned_weight / total_weight, 1) if total_weight else 100.0
        )

    if report.category_scores:
        report.overall_score = round(
            sum(report.category_scores.values()) / len(report.category_scores), 1
        )


def _check_https(report: AuditReport, parsed_url) -> None:
    report.findings.append(
        AuditFinding(
            category="security",
            check="https",
            passed=parsed_url.scheme == "https",
            message="Site is served over HTTPS"
            if parsed_url.scheme == "https"
            else "Site is not served over HTTPS",
            weight=3,
        )
    )


def _check_performance(report: AuditReport, elapsed_ms: float) -> None:
    passed = elapsed_ms < 1500
    report.findings.append(
        AuditFinding(
            category="performance",
            check="response_time",
            passed=passed,
            message=f"Initial response took {elapsed_ms:.0f}ms",
            weight=2,
        )
    )


def _check_title(report: AuditReport, soup: BeautifulSoup) -> None:
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    passed = 10 <= len(title) <= 60
    report.findings.append(
        AuditFinding(
            category="seo",
            check="title_tag",
            passed=passed,
            message=f"Title tag is {len(title)} characters"
            if title
            else "Missing <title> tag",
            weight=2,
        )
    )


def _check_meta_description(report: AuditReport, soup: BeautifulSoup) -> None:
    tag = soup.find("meta", attrs={"name": "description"})
    content = (tag.get("content") or "").strip() if tag else ""
    passed = 50 <= len(content) <= 160
    report.findings.append(
        AuditFinding(
            category="seo",
            check="meta_description",
            passed=passed,
            message=f"Meta description is {len(content)} characters"
            if content
            else "Missing meta description",
            weight=2,
        )
    )


def _check_headings(report: AuditReport, soup: BeautifulSoup) -> None:
    h1_count = len(soup.find_all("h1"))
    passed = h1_count == 1
    report.findings.append(
        AuditFinding(
            category="seo",
            check="h1_count",
            passed=passed,
            message=f"Page has {h1_count} <h1> tag(s), expected exactly 1",
            weight=1,
        )
    )


def _check_images_alt(report: AuditReport, soup: BeautifulSoup) -> None:
    images = soup.find_all("img")
    missing_alt = [img for img in images if not (img.get("alt") or "").strip()]
    passed = not missing_alt
    report.findings.append(
        AuditFinding(
            category="accessibility",
            check="image_alt_text",
            passed=passed,
            message=(
                "All images have alt text"
                if passed
                else f"{len(missing_alt)}/{len(images)} images missing alt text"
            ),
            weight=2,
        )
    )


def _check_viewport(report: AuditReport, soup: BeautifulSoup) -> None:
    tag = soup.find("meta", attrs={"name": "viewport"})
    report.findings.append(
        AuditFinding(
            category="mobile",
            check="viewport_meta",
            passed=tag is not None,
            message="Viewport meta tag present" if tag else "Missing viewport meta tag",
            weight=3,
        )
    )


def _check_canonical(report: AuditReport, soup: BeautifulSoup, final_url: str) -> None:
    tag = soup.find("link", attrs={"rel": "canonical"})
    report.findings.append(
        AuditFinding(
            category="seo",
            check="canonical_tag",
            passed=tag is not None,
            message="Canonical tag present" if tag else "Missing canonical link tag",
            weight=1,
        )
    )


def _check_security_headers(report: AuditReport, headers: httpx.Headers) -> None:
    required = ["content-security-policy", "x-frame-options", "strict-transport-security"]
    missing = [h for h in required if h not in headers]
    report.findings.append(
        AuditFinding(
            category="security",
            check="security_headers",
            passed=not missing,
            message="Recommended security headers present"
            if not missing
            else f"Missing security headers: {', '.join(missing)}",
            weight=2,
        )
    )


async def _check_robots_and_sitemap(report: AuditReport, base_url: str) -> None:
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(robots_url)
            passed = resp.status_code == 200
    except httpx.HTTPError:
        passed = False

    report.findings.append(
        AuditFinding(
            category="seo",
            check="robots_txt",
            passed=passed,
            message="robots.txt found" if passed else "robots.txt not found",
            weight=1,
        )
    )
