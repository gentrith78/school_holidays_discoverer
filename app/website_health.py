# app/utils/website_health.py
from __future__ import annotations
import logging
import time
import re
from dataclasses import dataclass
from typing import Optional, Dict
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class WebsiteHealth:
    input_url: str
    final_url: Optional[str]
    is_working: bool
    reason: str
    http_status: Optional[int]
    tls_ok: Optional[bool]
    elapsed_ms: int
    content_type: Optional[str]
    content_bytes: Optional[int]
    has_html_title: Optional[bool]
    server: Optional[str]
    tried_http_downgrade: bool


class WebsiteHealthChecker:
    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 2,
        backoff_factor: float = 0.3,
        user_agent: str = "Mozilla/5.0 (compatible; SchoolChecker/1.0)"
    ):
        self.timeout = timeout

        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["HEAD", "GET"]),
            raise_on_status=False,
        )

        self.s = requests.Session()
        self.s.headers.update({"User-Agent": user_agent})
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.s.mount("http://", adapter)
        self.s.mount("https://", adapter)
        self.log = logging.getLogger("main_logger")

    def is_usable(self, url: str) -> bool:
        """
        Return True if the website is alive enough to process:
        - HTTP status in 200–399
        - OR explicitly marked as "blocked" (e.g. Cloudflare 403/503)
        Return False if unreachable (timeout, DNS failure, connection refused, etc.)
        """
        health = self.check(url)

        # Accept if site gave us a good status
        if health.http_status and 200 <= health.http_status < 400:
            self.log.info("Website Health: OK")
            return True

        # Accept if site is "blocked" but reachable
        if health.reason.startswith("blocked"):
            self.log.info("Website Health: Blocked -- Can continue...")
            return True

        self.log.info(f"Broken Website:{health}")
        self.log.info(f"Skipping school because website is broken")

        return False

    def check(self, url: str) -> WebsiteHealth:
        """
        Returns a WebsiteHealth with:
         - is_working=True if we got a 2xx/3xx and (some content or a valid HEAD),
         - tls_ok=False if we only succeeded with verify=False or via http downgrade.
        """
        start = time.time()
        tls_ok = None
        tried_http_downgrade = False

        # 1) normalize url (default https)
        norm = self._normalize_url(url)

        # 2) try HTTPS with cert verification
        r, reason = self._probe(norm, verify=True)
        if r is None and "SSLError" in reason:
            # 3) retry HTTPS without verification (capture tls_ok=False)
            r, reason = self._probe(norm, verify=False)
            tls_ok = False

        if r is None and "SSLError" in reason:
            # 4) try HTTP downgrade (some sites have broken TLS)
            http_url = self._downgrade_to_http(norm)
            tried_http_downgrade = True
            r, reason = self._probe(http_url, verify=False)
            tls_ok = False

        elapsed_ms = int((time.time() - start) * 1000)

        if r is not None:
            status_ok = 200 <= r.status_code < 400
            content_len = int(r.headers.get("Content-Length", "0") or 0)
            body_len = len(r.content) if r.request.method == "GET" else content_len
            has_html_title = None
            ctype = r.headers.get("Content-Type")

            if r.request.method == "GET" and ctype and "html" in ctype.lower():
                txt = r.text[:5000]
                has_html_title = bool(re.search(r"<title[^>]*>.*?</title>", txt, flags=re.IGNORECASE | re.DOTALL))

            is_working = bool(status_ok and (r.request.method == "HEAD" or body_len > 0))
            # If we succeeded with verify=True at any point, tls_ok=True; else if we only succeeded w/o verify, tls_ok is already False.
            if tls_ok is None:
                tls_ok = True

            return WebsiteHealth(
                input_url=url,
                final_url=r.url,
                is_working=is_working,
                reason="ok" if is_working else f"http_status_{r.status_code}",
                http_status=r.status_code,
                tls_ok=tls_ok,
                elapsed_ms=elapsed_ms,
                content_type=ctype,
                content_bytes=body_len,
                has_html_title=has_html_title,
                server=r.headers.get("Server"),
                tried_http_downgrade=tried_http_downgrade,
            )

        return WebsiteHealth(
            input_url=url,
            final_url=None,
            is_working=False,
            reason=reason or "unknown_error",
            http_status=None,
            tls_ok=tls_ok,
            elapsed_ms=elapsed_ms,
            content_type=None,
            content_bytes=None,
            has_html_title=None,
            server=None,
            tried_http_downgrade=tried_http_downgrade,
        )

    # ---- internals ----

    def _probe(self, url: str, verify: bool) -> tuple[Optional[requests.Response], Optional[str]]:
        """
        Try HEAD first; if 405/403/404 or missing Content-Length, fall back to GET.
        """
        try:
            r = self.s.head(url, allow_redirects=True, timeout=self.timeout, verify=verify)
            if r.status_code in (405, 403, 404) or not r.headers.get("Content-Length"):
                r = self.s.get(url, allow_redirects=True, timeout=self.timeout, verify=verify, stream=False)
            return r, None
        except requests.exceptions.SSLError:
            return None, "SSLError"
        except requests.exceptions.ConnectTimeout:
            return None, "timeout_connect"
        except requests.exceptions.ReadTimeout:
            return None, "timeout_read"
        except requests.exceptions.ConnectionError:
            return None, "connection_error"
        except Exception as e:
            return None, f"exception_{type(e).__name__}"

    @staticmethod
    def _normalize_url(url: str) -> str:
        p = urlparse(url.strip())
        scheme = p.scheme or "https"
        netloc = p.netloc or p.path
        path = p.path if p.netloc else "/"
        return urlunparse((scheme, netloc, path if path else "/", "", "", ""))

    @staticmethod
    def _downgrade_to_http(url: str) -> str:
        p = urlparse(url)
        return urlunparse(("http", p.netloc, p.path or "/", "", "", ""))


