#!/usr/bin/env python3
"""
Query fund ID from datayes API using browser session cookies.

Cookie sources (tried in order):
  1. --cookies: raw cookie header string (for manual testing)
  2. Browser control server HTTP API (default http://127.0.0.1:18791)

The control server requires auth via --token or $OPENCLAW_GATEWAY_TOKEN.
Inside the container, the env var is set automatically.

Usage:
    python3 fund_search.py <keyword>
    python3 fund_search.py <keyword> --browser-url URL --token TOKEN
    python3 fund_search.py <keyword> --cookies "cloud-sso-token=xxx; cloud-anonymous-token=yyy"

Examples:
    python3 fund_search.py 006282
    python3 fund_search.py "摩根欧洲"

Output (JSON to stdout):
    {
        "success": true,
        "funds": [
            {"symbol": "006282", "name": "摩根欧洲动力策略股票(QDII)-A", "id": "MUTUAL-10011892",
             "detail_url": "https://r.datayes.com/mof/app/fund/detail/MUTUAL-10011892"}
        ],
        "source": "control:http://127.0.0.1:18791"
    }

On error:
    {"success": false, "error": "..."}
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


DEFAULT_BROWSER_URL = "http://127.0.0.1:18791"
DATAYES_API_URL = "https://gw.datayes.com/mom_fund_research/api/account/mutual/associateSearch"
DATAYES_ORIGIN = "https://r.datayes.com"


def get_browser_cookies(browser_url: str, auth_token: str = "") -> list[dict]:
    """Fetch cookies from the openclaw browser control server."""
    url = f"{browser_url}/cookies?profile=openclaw"
    req = urllib.request.Request(url, method="GET")
    if auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("cookies", [])
    except Exception as e:
        raise RuntimeError(f"Failed to get browser cookies: {e}") from e


def build_cookie_header(cookies: list[dict], domain_filter: str = "") -> str:
    """Build a Cookie header string from browser cookies, optionally filtering by domain."""
    parts = []
    for c in cookies:
        if domain_filter and not c.get("domain", "").endswith(domain_filter):
            continue
        name = c.get("name", "")
        value = c.get("value", "")
        if name:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def search_fund(keyword: str, cookie_header: str) -> dict:
    """Call the datayes associateSearch API."""
    payload = json.dumps({
        "associateSearchField": {
            "name": "all",
            "op": "LIKE",
            "values": [keyword]
        }
    }).encode("utf-8")

    req = urllib.request.Request(DATAYES_API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Cookie", cookie_header)
    req.add_header("Origin", DATAYES_ORIGIN)
    req.add_header("Referer", f"{DATAYES_ORIGIN}/")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"API returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"API request failed: {e}") from e


def main():
    parser = argparse.ArgumentParser(description="Search fund ID on datayes")
    parser.add_argument("keyword", help="Fund code or name to search (e.g. 006282)")
    parser.add_argument("--browser-url", default=os.environ.get("OPENCLAW_BROWSER_URL", DEFAULT_BROWSER_URL),
                        help=f"Browser control server URL (default: {DEFAULT_BROWSER_URL})")
    parser.add_argument("--token", default=os.environ.get("OPENCLAW_GATEWAY_TOKEN", ""),
                        help="Auth token for browser control server (default: $OPENCLAW_GATEWAY_TOKEN)")
    parser.add_argument("--cookies", default="",
                        help="Raw cookie header string for manual testing (e.g. 'cloud-sso-token=xxx')")
    args = parser.parse_args()

    try:
        cookie_header = ""
        source = ""

        # Strategy 1: explicit cookie string
        if args.cookies:
            cookie_header = args.cookies
            source = "manual"

        # Strategy 2: browser control server
        if not cookie_header:
            try:
                cookies = get_browser_cookies(args.browser_url, auth_token=args.token)
                cookie_header = build_cookie_header(cookies, domain_filter="datayes.com")
                source = f"control:{args.browser_url}"
            except Exception as e:
                print(json.dumps({"success": False,
                    "error": f"Browser bridge unavailable ({e}). Use --cookies for manual testing.",
                    "hint": "This script works automatically during agent sessions (bridge active). "
                            "For manual testing, copy cookies from browser DevTools and pass via --cookies."},
                    ensure_ascii=False))
                sys.exit(1)

        if not cookie_header:
            print(json.dumps({"success": False,
                "error": f"No datayes.com cookies found (source: {source}). Login to datayes first."}))
            sys.exit(1)

        result = search_fund(args.keyword, cookie_header)

        if not result.get("success"):
            code = result.get("code", "")
            msg = result.get("message", "Unknown error")
            print(json.dumps({"success": False, "error": f"API error ({code}): {msg}"}))
            sys.exit(1)

        funds = result.get("data", {}).get("fund", [])
        output_funds = []
        for f in funds:
            fund_id = f.get("id", "")
            output_funds.append({
                "symbol": f.get("symbol", ""),
                "name": f.get("name", ""),
                "id": fund_id,
                "detail_url": f"https://r.datayes.com/mof/app/fund/detail/{fund_id}" if fund_id else ""
            })

        print(json.dumps({"success": True, "funds": output_funds, "source": source}, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
