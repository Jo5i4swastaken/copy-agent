"""
Web fetching tool for the Copy Agent.

Fetches webpage content and returns readable text — useful for
competitive analysis, studying landing pages, and reviewing existing copy.

Uses only stdlib (urllib) so no extra dependencies are needed.
"""

import re
import ssl
import urllib.request
import urllib.error

from omniagents import function_tool

# macOS Python often lacks linked SSL certs — create an unverified
# context as a fallback so web_fetch doesn't break on every request.
try:
    _SSL_CTX = ssl.create_default_context()
except ssl.SSLError:
    _SSL_CTX = ssl._create_unverified_context()


def _html_to_text(html: str) -> str:
    """Strip HTML tags and collapse whitespace into readable text."""
    # Remove script and style blocks
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    html = re.sub(r"<(br|p|div|h[1-6]|li|tr|blockquote)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@function_tool
def web_fetch(url: str, max_chars: int = 15000) -> str:
    """Fetch a webpage and return its text content. Useful for reading
    landing pages, competitor copy, blog posts, or any public web page.

    Args:
        url: The full URL to fetch (e.g. 'https://example.com/pricing').
        max_chars: Maximum characters to return (default 15000). Truncates
            with a notice if the page is longer.
    """
    if not url.startswith(("http://", "https://")):
        return f"Error: URL must start with http:// or https://. Got: {url}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CopyAgent/1.0)"},
    )

    try:
        # Try with default SSL first, fall back to unverified if certs are missing
        try:
            resp_handle = urllib.request.urlopen(req, timeout=20, context=_SSL_CTX)
        except urllib.error.URLError as ssl_err:
            if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err):
                ctx = ssl._create_unverified_context()
                resp_handle = urllib.request.urlopen(req, timeout=20, context=ctx)
            else:
                raise
        with resp_handle as response:
            content_type = response.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            raw = response.read()
            text = raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        return f"Error: HTTP {e.code} when fetching {url}"
    except urllib.error.URLError as e:
        return f"Error: Could not fetch {url} — {e.reason}"
    except TimeoutError:
        return f"Error: Request timed out after 20 seconds for {url}"
    except Exception as e:
        return f"Error: Failed to fetch {url} — {e}"

    # If it's HTML, convert to readable text
    if "html" in content_type.lower():
        text = _html_to_text(text)

    # Truncate if needed
    total_len = len(text)
    if total_len > max_chars:
        text = text[:max_chars] + f"\n\n[Truncated — {total_len} total characters. Increase max_chars to see more.]"

    return f"Fetched: {url}\nContent-Type: {content_type}\n\n{text}"
