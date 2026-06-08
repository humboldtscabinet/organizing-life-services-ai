"""
Unit tests for the SEO crawler's pure-ish logic.

Network calls are mocked, so these run offline and fast. They cover the two
pieces most likely to regress: per-page issue detection (`audit_page`) and the
sitemap bot-challenge detection added to `discover_urls_verbose`.
"""

from unittest.mock import patch

from app.services import seo_crawler


class _FakeResponse:
    def __init__(self, *, status=200, content=b"", ctype="text/html", url="https://x/"):
        self.status_code = status
        self.content = content
        self.text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
        self.headers = {"Content-Type": ctype}
        self.url = url

    @property
    def ok(self):
        return 200 <= self.status_code < 400


GOOD_HTML = b"""
<html><head>
  <title>Estate Sale Services in Palm Harbor | Organizing Life Services</title>
  <meta name="description" content="Professional estate sale and downsizing services across Pinellas County with full-service setup, pricing, and cleanup.">
  <link rel="canonical" href="https://organizinglifeservices.com/">
  <meta property="og:title" content="Estate Sales">
  <script type="application/ld+json">{"@type": "LocalBusiness"}</script>
</head><body>
  <h1>Estate Sale Services</h1>
  <p>%s</p>
  <img src="a.jpg" alt="estate sale setup">
</body></html>
""" % (b"word " * 250)


def test_audit_page_clean_page_has_no_issues():
    with patch.object(seo_crawler.requests, "get",
                      return_value=_FakeResponse(content=GOOD_HTML)):
        info = seo_crawler.audit_page("https://organizinglifeservices.com/")
    assert info["ok"] is True
    assert info["status"] == 200
    assert info["h1_count"] == 1
    assert "LocalBusiness" in info["schema_types"]
    assert info["issues"] == []


def test_audit_page_flags_missing_elements():
    html = b"<html><head></head><body><p>too short</p></body></html>"
    with patch.object(seo_crawler.requests, "get",
                      return_value=_FakeResponse(content=html)):
        info = seo_crawler.audit_page("https://organizinglifeservices.com/x")
    issues = set(info["issues"])
    assert "missing_title" in issues
    assert "missing_meta_description" in issues
    assert "missing_h1" in issues
    assert "missing_canonical" in issues
    assert "missing_schema" in issues
    assert "thin_content" in issues


def test_audit_page_non_html_skips_parsing():
    with patch.object(seo_crawler.requests, "get",
                      return_value=_FakeResponse(content=b"%PDF-1.4", ctype="application/pdf")):
        info = seo_crawler.audit_page("https://organizinglifeservices.com/file.pdf")
    assert info["ok"] is True
    assert "issues" not in info  # parsing short-circuited for non-HTML


def test_audit_page_handles_request_exception():
    with patch.object(seo_crawler.requests, "get", side_effect=RuntimeError("boom")):
        info = seo_crawler.audit_page("https://organizinglifeservices.com/down")
    assert info["ok"] is False
    assert "boom" in info["error"]


def test_discover_urls_detects_bot_challenge():
    """A 200 response whose body is an HTML challenge page must be flagged."""
    # Real challenge pages aren't valid XML (unclosed <meta>/<br>, HTML
    # entities), which is exactly what trips ET.fromstring.
    challenge = _FakeResponse(
        content=(
            b"<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            b"<title>Verifying your connection...</title></head>"
            b"<body><br><p>One moment&nbsp;please</p></body></html>"
        ),
        ctype="text/html",
    )
    with patch.object(seo_crawler.requests, "get", return_value=challenge):
        urls, diag = seo_crawler.discover_urls_verbose("https://organizinglifeservices.com/")
    assert urls == []
    assert diag["bot_challenge_detected"] is True
    assert diag["sitemap_errors"], "expected the parse failure to be recorded"


def test_discover_urls_parses_sitemap_urlset():
    xml = (
        b'<?xml version="1.0"?>'
        b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://organizinglifeservices.com/a</loc></url>"
        b"<url><loc>https://organizinglifeservices.com/b</loc></url>"
        b"</urlset>"
    )
    with patch.object(seo_crawler.requests, "get",
                      return_value=_FakeResponse(content=xml, ctype="application/xml")):
        urls, diag = seo_crawler.discover_urls_verbose("https://organizinglifeservices.com/")
    assert urls == [
        "https://organizinglifeservices.com/a",
        "https://organizinglifeservices.com/b",
    ]
    assert diag["bot_challenge_detected"] is False
