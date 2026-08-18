#!/usr/bin/env python3
"""
Pepper Network Deal Scraper - Cloudflare Bypass Multi-Strategy

Cloudflare "Managed Challenge" on Pepper sites (Slickdeals, MyDealz, HotUKDeals, etc.)
requires JavaScript execution + sometimes CAPTCHA solving. This script provides
multiple strategies to handle this:

Strategy 0: Direct RSS with multiple HTTP backends (fastest, no dependencies)
  - Tries direct RSS access with multiple HTTP libraries
  - Some Pepper sites allow direct RSS access depending on network conditions
  - Tries backends in order: urllib → cloudscraper → curl_cffi → requests
  - No special dependencies required (urllib is stdlib); others optional

Strategy 1: undetected-chromedriver (best automated approach)
  - Uses patched Chrome that bypasses bot detection
  - Can solve most Cloudflare JS challenges automatically
  - Requires: pip install undetected-chromedriver selenium
  - Requires: Chrome/Chromium installed on your machine

Strategy 2: Manual Cookie Injection
  - User opens browser manually, solves CAPTCHA, copies cookies
  - Script uses those cookies to access RSS/API directly
  - Works when Strategy 1 fails (CAPTCHA required)
  - No special dependencies needed

Strategy 3: Google Cache Fallback
  - Uses Google search to discover deal URLs
  - Then fetches individual pages through Google cache
  - No Cloudflare interaction needed

Strategy 4: Third-Party Scraping API (ZenRows / ScraperAPI)
  - Uses commercial scraping services with built-in Cloudflare bypass
  - Most reliable approach, but requires API key (paid service)
  - Free tiers available (ZenRows: 1000 free requests/month)
  - Requires: pip install requests

Strategy 5: WebSearch Discovery (platform integration)
  - Uses platform's built-in search to discover deal posts
  - Generates search URLs for manual verification
  - No dependencies, works anywhere

Usage:
  python pepper_scraper_full.py -k navimow                          # Auto (try 0→1→2→3→4→5)
  python pepper_scraper_full.py -k navimow --strategy direct         # Strategy 0
  python pepper_scraper_full.py -k navimow --strategy browser        # Strategy 1
  python pepper_scraper_full.py -k navimow --strategy cookie         # Strategy 2
  python pepper_scraper_full.py -k navimow --strategy cache          # Strategy 3
  python pepper_scraper_full.py -k navimow --strategy api            # Strategy 4
  python pepper_scraper_full.py -k navimow --strategy api --api-key YOUR_KEY
  python pepper_scraper_full.py -k navimow --strategy all            # Try all strategies
  python pepper_scraper_full.py -k navimow -c de,uk                  # Specific countries
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSL context fix for ScraperAPI (requests library has SSLEOFError on some systems)
import ssl as _ssl
_SSL_CTX = _ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = _ssl.CERT_NONE

class _ScraperResponse:
    """Response wrapper for urllib-based ScraperAPI calls."""
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


# ═══════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════

PEPPER_SITES = [
    {"country": "us", "site": "Slickdeals", "domain": "slickdeals.net",
     "search_url": "https://slickdeals.net/search?q={q}",
     "rss_url": "https://slickdeals.net/rss/search?q={q}"},
    {"country": "de", "site": "MyDealz", "domain": "mydealz.de",
     "search_url": "https://www.mydealz.de/search?q={q}",
     "rss_url": "https://www.mydealz.de/rss/search?q={q}"},
    {"country": "uk", "site": "HotUKDeals", "domain": "hotukdeals.com",
     "search_url": "https://www.hotukdeals.com/search?q={q}",
     "rss_url": "https://www.hotukdeals.com/rss/search?q={q}"},
    {"country": "fr", "site": "Dealabs", "domain": "dealabs.com",
     "search_url": "https://www.dealabs.com/search?q={q}",
     "rss_url": "https://www.dealabs.com/rss/search?q={q}"},
    {"country": "es", "site": "Chollometro", "domain": "chollometro.com",
     "search_url": "https://www.chollometro.com/search?q={q}",
     "rss_url": "https://www.chollometro.com/rss/search?q={q}"},
    {"country": "mx", "site": "Promodescuentos", "domain": "promodescuentos.com",
     "search_url": "https://www.promodescuentos.com/search?q={q}",
     "rss_url": "https://www.promodescuentos.com/rss/search?q={q}"},
    {"country": "pl", "site": "Pepper.pl", "domain": "pepper.pl",
     "search_url": "https://www.pepper.pl/search?q={q}",
     "rss_url": "https://www.pepper.pl/rss/search?q={q}"},
    {"country": "br", "site": "Pelando", "domain": "pelando.com.br",
     "search_url": "https://www.pelando.com.br/search?q={q}",
     "rss_url": "https://www.pelando.com.br/rss/search?q={q}"},
    {"country": "br", "site": "Promobit", "domain": "promobit.com.br",
     "search_url": "https://www.promobit.com.br/search?q={q}",
     "rss_url": "https://www.promobit.com.br/rss/search?q={q}"},
    {"country": "ca", "site": "RedFlagDeals", "domain": "redflagdeals.com",
     "search_url": "https://forums.redflagdeals.com/search/?q={q}",
     "rss_url": "https://forums.redflagdeals.com/rss/"},
    {"country": "au", "site": "OzBargain", "domain": "ozbargain.com.au",
     "search_url": "https://www.ozbargain.com.au/search?q={q}",
     "rss_url": "https://www.ozbargain.com.au/rss.xml"},
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 0: Direct RSS with multiple HTTP backends
# ═══════════════════════════════════════════════════════════════════════

def scrape_with_direct_rss(keyword, sites=PEPPER_SITES):
    """
    Strategy 0: Try direct RSS access with multiple HTTP backends.
    Some Pepper sites (MyDealz, Dealabs, Chollometro, Promodescuentos, Pepper.pl)
    allow direct RSS access depending on network conditions.

    Tries backends in order: urllib → cloudscraper → curl_cffi → requests
    """
    import urllib.request
    import ssl

    print("\n  Strategy 0: Direct RSS with multiple HTTP backends")

    all_posts = []
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    common_headers = {
        "User-Agent": user_agent,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for site in sites:
        rss_url = site["rss_url"].format(q=urllib.parse.quote(keyword))
        print(f"  [{site['country'].upper()}] {site['site']}...", end=" ", flush=True)

        xml_text = ""
        backend_used = ""

        # ── Backend 1: urllib (stdlib, always available) ──────────────
        if not xml_text:
            try:
                req = urllib.request.Request(rss_url, headers=common_headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    xml_text = resp.read().decode("utf-8", errors="replace")
                if xml_text and "Just a moment" not in xml_text and "<" in xml_text:
                    backend_used = "urllib"
                else:
                    xml_text = ""  # Cloudflare blocked or empty, try next backend
            except Exception:
                xml_text = ""

        # ── Backend 2: cloudscraper ───────────────────────────────────
        if not xml_text:
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(rss_url, headers=common_headers, timeout=20)
                if resp.status_code == 200 and resp.text:
                    xml_text = resp.text
                    if "Just a moment" in xml_text:
                        xml_text = ""
                    else:
                        backend_used = "cloudscraper"
            except ImportError:
                pass  # cloudscraper not installed, skip
            except Exception:
                xml_text = ""

        # ── Backend 3: curl_cffi (TLS fingerprint impersonation) ──────
        if not xml_text:
            try:
                from curl_cffi import requests as curl_requests
                resp = curl_requests.get(rss_url, headers=common_headers,
                                         timeout=20, impersonate="chrome")
                if resp.status_code == 200 and resp.text:
                    xml_text = resp.text
                    if "Just a moment" in xml_text:
                        xml_text = ""
                    else:
                        backend_used = "curl_cffi"
            except ImportError:
                pass  # curl_cffi not installed, skip
            except Exception:
                xml_text = ""

        # ── Backend 4: requests (standard library fallback) ──────────
        if not xml_text:
            try:
                import requests
                resp = requests.get(rss_url, headers=common_headers, timeout=20,
                                     verify=False)
                if resp.status_code == 200 and resp.text:
                    xml_text = resp.text
                    if "Just a moment" in xml_text:
                        xml_text = ""
                    else:
                        backend_used = "requests"
            except ImportError:
                pass  # requests not installed, skip
            except Exception:
                xml_text = ""

        # ── Parse the result if any backend succeeded ─────────────────
        if not xml_text:
            print("BLOCKED (all backends failed)")
            continue

        try:
            posts = parse_rss_xml(xml_text, site, keyword)
            if posts:
                print(f"FOUND {len(posts)} posts (via {backend_used})")
                all_posts.extend(posts)
            else:
                print(f"0 posts (via {backend_used})")
        except Exception as e:
            print(f"ERROR: {str(e)[:60]}")

        time.sleep(1)  # Rate limit between sites

    return all_posts


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 1: undetected-chromedriver
# ═══════════════════════════════════════════════════════════════════════

def scrape_with_undetected_chromedriver(keyword, sites=PEPPER_SITES):
    """
    Use undetected-chromedriver to bypass Cloudflare.
    This patched Chrome driver avoids bot detection signals.
    """
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("  [ERROR] undetected-chromedriver not installed.")
        print("         Install with: pip install undetected-chromedriver selenium")
        return []

    print("\n  Strategy 1: undetected-chromedriver")
    print("  Launching patched Chrome browser...")

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Set a realistic user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    # Auto-detect installed Chrome major version to avoid chromedriver mismatch
    chrome_major = None
    try:
        import subprocess as _sp, re as _re, os as _os
        for _p in (r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                   r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"):
            if _os.path.exists(_p):
                _out = _sp.check_output([_p, "--version"], stderr=_sp.STDOUT, timeout=10).decode(errors="ignore")
                _m = _re.search(r"(\d+)\.", _out)
                if _m:
                    chrome_major = int(_m.group(1))
                    print(f"  Detected Chrome major version: {chrome_major}")
                    break
    except Exception as _e:
        print(f"  [WARN] Could not auto-detect Chrome version: {_e}")

    try:
        driver = uc.Chrome(options=options, version_main=151)
    except Exception as e:
        print(f"  [ERROR] Failed to launch Chrome: {e}")
        print("         Make sure Chrome/Chromium is installed on your machine.")
        return []

    all_posts = []

    for site in sites:
        search_url = site["search_url"].format(q=urllib.parse.quote(keyword))
        print(f"  [{site['country'].upper()}] {site['site']}...", end=" ", flush=True)

        try:
            driver.get(search_url)

            # Wait for Cloudflare challenge to resolve
            # Cloudflare challenge page has title "Just a moment..."
            time.sleep(5)  # Give Cloudflare time to run JS

            # Check if we're still on challenge page
            if "Just a moment" in driver.title:
                # Wait up to 15 more seconds for challenge to resolve
                for _ in range(15):
                    time.sleep(1)
                    if "Just a moment" not in driver.title:
                        break

            if "Just a moment" in driver.title:
                print("BLOCKED (Cloudflare challenge not resolved)")
                # Try to find and click the challenge checkbox
                try:
                    iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src*='challenges.cloudflare.com']")
                    driver.switch_to.frame(iframe)
                    checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    checkbox.click()
                    driver.switch_to.default_content()
                    time.sleep(5)
                except Exception:
                    pass

                if "Just a moment" in driver.title:
                    continue

            # Wait for page content to load
            time.sleep(2)

            # Extract page source and parse
            page_source = driver.page_source
            posts = parse_pepper_html(page_source, site, keyword)

            if posts:
                print(f"FOUND {len(posts)} posts")
                all_posts.extend(posts)
            else:
                print("0 posts (no matches on page)")

        except Exception as e:
            print(f"ERROR: {str(e)[:60]}")

        time.sleep(2)  # Rate limit between sites

    driver.quit()
    return all_posts


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 2: Manual Cookie Injection
# ═══════════════════════════════════════════════════════════════════════

def get_cookies_from_user(domain):
    """
    Ask user to manually visit the site, solve CAPTCHA, and paste cookies.
    Returns cookie string. Returns None if running non-interactively.
    """
    # Check if stdin is interactive (skip in automated mode)
    if not sys.stdin.isatty():
        print(f"  [SKIP] Cookie extraction requires interactive terminal (non-interactive mode detected)")
        return None

    print(f"\n  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │  Manual Cookie Extraction for {domain:25s}        │")
    print(f"  └──────────────────────────────────────────────────────────┘")
    print(f"  1. Open your browser and go to: https://{domain}")
    print(f"  2. If Cloudflare challenge appears, complete the CAPTCHA")
    print(f"  3. Once the page loads, open Developer Tools (F12)")
    print(f"  4. Go to Network tab → click any request → Headers")
    print(f"  5. Find the 'Cookie' header and copy its full value")
    print(f"  6. Paste it below and press Enter:\n")

    try:
        cookie = input("  Cookie: ").strip()
        return cookie if cookie else None
    except (EOFError, KeyboardInterrupt):
        return None


def scrape_with_cookies(keyword, sites=PEPPER_SITES):
    """
    Use manually obtained cookies to access Pepper site RSS/API.
    Cookies from a real browser session bypass Cloudflare.
    """
    import urllib.request
    import ssl

    print("\n  Strategy 2: Manual Cookie Injection")

    # Ask user for cookies for each site that needs them
    site_cookies = {}
    for site in sites:
        cookie = get_cookies_from_user(site["domain"])
        if cookie:
            site_cookies[site["domain"]] = cookie

    if not site_cookies:
        print("  No cookies provided. Skipping Strategy 2.")
        return []

    all_posts = []
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for site in sites:
        domain = site["domain"]
        if domain not in site_cookies:
            continue

        rss_url = site["rss_url"].format(q=urllib.parse.quote(keyword))
        print(f"  [{site['country'].upper()}] {site['site']}...", end=" ", flush=True)

        try:
            req = urllib.request.Request(rss_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Cookie": site_cookies[domain],
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "en-US,en;q=0.9",
            })

            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                xml_text = resp.read().decode("utf-8", errors="replace")

            if "Just a moment" in xml_text:
                print("BLOCKED (cookie expired or invalid)")
                continue

            posts = parse_rss_xml(xml_text, site, keyword)
            if posts:
                print(f"FOUND {len(posts)} posts")
                all_posts.extend(posts)
            else:
                print("0 posts (no matches)")

        except Exception as e:
            print(f"ERROR: {str(e)[:60]}")

    return all_posts


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 3: Google Cache / Search Engine Fallback
# ═══════════════════════════════════════════════════════════════════════

def scrape_with_google_cache(keyword, sites=PEPPER_SITES):
    """
    Use Google search to find cached Pepper site pages.
    Google caches pages and serves them without Cloudflare.
    """
    import urllib.request
    import ssl

    print("\n  Strategy 3: Google Cache / Search Engine Fallback")

    all_posts = []
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for site in sites:
        domain = site["domain"]
        # Google search: site:domain keyword
        google_url = f"https://www.google.com/search?q=site:{domain}+{urllib.parse.quote(keyword)}&num=20"

        print(f"  [{site['country'].upper()}] {site['site']}...", end=" ", flush=True)

        try:
            req = urllib.request.Request(google_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })

            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # Extract URLs from Google search results that point to the Pepper site
            escaped_domain = re.escape(domain)
            url_pattern = rf'https?://(?:www\.)?{escaped_domain}/[^\s"\'<>]+'
            found_urls = re.findall(url_pattern, html)

            # Also try to extract titles
            # Google results have titles in <h3> tags
            title_pattern = r'<h3[^>]*>(.*?)</h3>'
            titles = re.findall(title_pattern, html, re.DOTALL)
            titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]

            # Match URLs with titles
            posts = []
            for i, url in enumerate(found_urls[:20]):  # Limit to 20 results
                title = titles[i] if i < len(titles) else ""
                if keyword.lower() in title.lower() or keyword.lower() in url.lower():
                    posts.append({
                        "site": site["site"],
                        "domain": domain,
                        "country": site["country"],
                        "title": title or url.split("/")[-1].replace("-", " "),
                        "link": url,
                        "pub_date": "",
                        "price": extract_price(title) or "",
                        "temperature": "",
                        "votes": "",
                        "comments_count": "",
                        "summary": "",
                        "source": "google_cache",
                    })

            if posts:
                print(f"FOUND {len(posts)} posts (via Google)")
                all_posts.extend(posts)
            else:
                print("0 posts (Google found no matches)")

        except Exception as e:
            print(f"ERROR: {str(e)[:60]}")

        time.sleep(1)  # Rate limit Google requests

    return all_posts


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 4: Third-Party Scraping API (ZenRows / ScraperAPI)
# ═══════════════════════════════════════════════════════════════════════

def scrape_with_api(keyword, sites=PEPPER_SITES, api_key="", api_provider="zenrows"):
    """
    Use third-party scraping API to bypass Cloudflare.
    
    Supported providers:
    - ScraperAPI: https://www.scraperapi.com/ (5000 free requests/month) [RECOMMENDED]
    - ZenRows: https://www.zenrows.com/ (1000 free requests/month)
    
    Uses urllib (not requests) to avoid SSL compatibility issues on some systems.
    Falls back from RSS to HTML search page when RSS returns 404.
    """
    import urllib.parse

    if not api_key:
        print("\n  Strategy 4: Third-Party Scraping API")
        print("  [SKIP] No API key provided.")
        print("  Get a FREE key from:")
        print("    - ScraperAPI: https://www.scraperapi.com/ (5000 free req/month) [RECOMMENDED]")
        print("    - ZenRows:    https://www.zenrows.com/  (1000 free req/month)")
        print("  Then run with: --strategy api --api-key YOUR_KEY --api-provider scraperapi")
        return []

    print(f"\n  Strategy 4: Third-Party Scraping API ({api_provider})")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")

    # Test API key
    try:
        test_url = "https://api.scraperapi.com/?api_key=" + api_key + "&url=https://httpbin.org/ip&render=false"
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90, context=_SSL_CTX) as resp:
            print(f"  API key valid! ({resp.read().decode()[:60]})")
    except Exception as e:
        print(f"  [ERROR] API key test failed: {str(e)[:80]}")
        return []

    all_posts = []
    cc_map = {"us": "us", "uk": "gb", "de": "de", "fr": "fr", "es": "es",
              "mx": "mx", "pl": "pl", "br": "br", "ca": "ca", "au": "au"}

    for site in sites:
        q = urllib.parse.quote(keyword)
        cc = cc_map.get(site.get("country", "us"), "us")
        posts = []

        # Build RSS URL
        rss_url = site["rss_url"].format(q=q)

        # Build HTML search URL (fallback)
        html_url = site.get("search_url", "").format(q=q)
        if not html_url:
            domain = site.get("domain", "")
            html_url = f"https://{domain}/search?q={q}"

        # Try RSS first
        print(f"  [{site.get('country','').upper()}] {site.get('name','')} (RSS)...", end=" ", flush=True)
        try:
            if api_provider == "scraperapi":
                api_url = (f"https://api.scraperapi.com/?api_key={api_key}"
                           f"&url={urllib.parse.quote(rss_url)}"
                           f"&render=true&country_code={cc}")
            else:  # zenrows
                api_url = (f"https://api.zenrows.com/v1/?apikey={api_key}"
                           f"&url={urllib.parse.quote(rss_url)}"
                           f"&js_render=true&premium_proxy=true&antibot=true")

            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status

            if status == 200 and ("<item" in body or "<rss" in body):
                posts = parse_pepper_rss_xml(body, site, keyword)
                if posts:
                    print(f"FOUND {len(posts)} posts")
                else:
                    print("0 posts (RSS ok)")
            elif status == 404:
                print("404, trying HTML...", end=" ", flush=True)
            else:
                print(f"HTTP {status}")
        except Exception as e:
            err = str(e)
            if "404" in err:
                print("404, trying HTML...", end=" ", flush=True)
            else:
                print(f"ERROR: {err[:60]}")

        # Fallback: HTML search page
        if not posts:
            print(f"HTML...", end=" ", flush=True)
            try:
                if api_provider == "scraperapi":
                    api_url = (f"https://api.scraperapi.com/?api_key={api_key}"
                               f"&url={urllib.parse.quote(html_url)}"
                               f"&render=true&country_code={cc}")
                else:
                    api_url = (f"https://api.zenrows.com/v1/?apikey={api_key}"
                               f"&url={urllib.parse.quote(html_url)}"
                               f"&js_render=true&premium_proxy=true&antibot=true")

                req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
                    body = resp.read().decode("utf-8", errors="replace")

                if "just a moment" in body.lower() or "请稍候" in body:
                    print("BLOCKED")
                else:
                    posts = extract_deals_from_html(body, site, keyword)
                    if posts:
                        print(f"FOUND {len(posts)} posts")
                    else:
                        print(f"0 posts (keyword appears {body.lower().count(keyword.lower())}x)")
            except Exception as e:
                print(f"ERROR: {str(e)[:60]}")

        all_posts.extend(posts)
        time.sleep(1)

    return all_posts


def parse_pepper_rss_xml(xml_text, site_info, keyword):
    """Parse RSS XML from ScraperAPI response."""
    import html as html_mod
    posts = []
    try:
        xml_clean = re.sub(r'<\?xml[^>]*\?>', '', xml_text, count=1)
        root = ET.fromstring(xml_clean)
    except Exception:
        return parse_pepper_rss_regex(xml_text, site_info, keyword)

    items = root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry')
    for item in items:
        title = link = pub_date = desc = ""
        t = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
        if t is not None and t.text:
            title = t.text.strip()
        l = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
        if l is not None:
            link = l.text.strip() if l.text else l.get('href', '')
        d = item.find('pubDate') or item.find('{http://www.w3.org/2005/Atom}published')
        if d is not None and d.text:
            pub_date = d.text.strip()
        de = item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary')
        if de is not None and de.text:
            desc = re.sub(r'<[^>]+>', '', de.text).strip()

        if keyword.lower() in (title + " " + desc).lower():
            posts.append({
                "site": site_info.get("name", ""), "domain": site_info.get("domain", ""),
                "country": site_info.get("country", ""), "title": title, "link": link,
                "pub_date": pub_date, "price": extract_price_from_text(title + " " + desc),
                "temperature": "", "votes": "", "comments_count": "",
                "summary": desc[:300], "source": f"api_{site_info.get('name','')}",
                "needs_browser": True
            })
    return posts


def parse_pepper_rss_regex(text, site_info, keyword):
    """Fallback regex RSS parser."""
    import html as html_mod
    posts = []
    blocks = re.findall(r'<(?:item|entry)[^>]*>(.*?)</(?:item|entry)>', text, re.DOTALL)
    for block in blocks:
        title_m = re.search(r'<title[^>]*>(.*?)</title>', block, re.DOTALL)
        link_m = re.search(r'<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>|<link[^>]*href="([^"]*)"', block, re.DOTALL)
        date_m = re.search(r'<(?:pubDate|published|updated)[^>]*>(.*?)</(?:pubDate|published|updated)>', block, re.DOTALL)
        desc_m = re.search(r'<(?:description|summary|content)[^>]*>(.*?)</(?:description|summary|content)>', block, re.DOTALL)
        title = html_mod.unescape(title_m.group(1).strip()) if title_m else ""
        link = ""
        if link_m:
            link = (link_m.group(1) or link_m.group(2) or "").strip()
        pub_date = date_m.group(1).strip() if date_m else ""
        desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""
        desc = html_mod.unescape(desc)
        if keyword.lower() in (title + " " + desc).lower():
            posts.append({
                "site": site_info.get("name", ""), "domain": site_info.get("domain", ""),
                "country": site_info.get("country", ""), "title": title, "link": link,
                "pub_date": pub_date, "price": extract_price_from_text(title + " " + desc),
                "temperature": "", "votes": "", "comments_count": "",
                "summary": desc[:300], "source": f"api_{site_info.get('name','')}",
                "needs_browser": True
            })
    return posts


def extract_deals_from_html(page_source, site_info, keyword):
    """Extract deal links from rendered HTML search page."""
    import html as html_mod
    posts = []
    anchor_pattern = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
    seen = set()
    for m in anchor_pattern.finditer(page_source):
        href = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        text = html_mod.unescape(text)
        if keyword.lower() in text.lower() and len(text) > 10 and href not in seen:
            seen.add(href)
            domain = site_info.get("domain", "")
            full_link = href if href.startswith("http") else f"https://{domain}{href}" if href.startswith("/") else f"https://{domain}/{href}"
            posts.append({
                "site": site_info.get("name", ""), "domain": domain,
                "country": site_info.get("country", ""), "title": text[:200],
                "link": full_link, "pub_date": "", "price": extract_price_from_text(text),
                "temperature": "", "votes": "", "comments_count": "",
                "summary": "", "source": f"api_html_{site_info.get('name','')}",
                "needs_browser": True
            })
    return posts


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 5: WebSearch Discovery (platform integration)
# ═══════════════════════════════════════════════════════════════════════

def scrape_with_websearch_discovery(keyword, sites=PEPPER_SITES):
    """
    Generate search URLs and instructions for manual verification.
    This strategy doesn't make HTTP requests - it produces a list of
    URLs that the user (or platform WebSearch tool) can check.

    This is the fallback when all automated strategies fail.
    """
    print("\n  Strategy 5: WebSearch Discovery (Manual Verification)")
    print("  Generating search URLs for manual checking...\n")

    all_posts = []

    for site in sites:
        search_url = site["search_url"].format(q=urllib.parse.quote(keyword))
        rss_url = site["rss_url"].format(q=urllib.parse.quote(keyword))
        google_search = f"https://www.google.com/search?q=site:{site['domain']}+{keyword}"

        print(f"  [{site['country'].upper()}] {site['site']}")
        print(f"    Site search:  {search_url}")
        print(f"    RSS feed:     {rss_url}")
        print(f"    Google cache: {google_search}")
        print()

        # Also create a placeholder post with search URL
        all_posts.append({
            "site": site["site"],
            "domain": site["domain"],
            "country": site["country"],
            "title": f"[MANUAL CHECK NEEDED] Search for '{keyword}' on {site['site']}",
            "link": search_url,
            "pub_date": "",
            "price": "",
            "temperature": "",
            "votes": "",
            "comments_count": "",
            "summary": f"Cloudflare blocks automated access. Visit {search_url} manually to check for deals.",
            "source": "websearch_discovery",
        })

    print("  ──────────────────────────────────────────────")
    print("  All automated strategies were blocked by Cloudflare.")
    print("  Please visit the URLs above in your browser to find deals.")
    print("  If you find a deal, copy its URL and use --strategy cookie")
    print("  to extract full data (temperature, votes, comments).")
    print()

    return all_posts


# ═══════════════════════════════════════════════════════════════════════
#  HTML/XML Parsing Functions
# ═══════════════════════════════════════════════════════════════════════

def extract_price(text):
    """Extract price from text."""
    if not text:
        return ""
    patterns = [
        r'[\$£€]\s?(\d{1,}(?:[.,]\d{2})?)',
        r'(\d{1,}(?:[.,]\d{2})?)\s?[\$£€]',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def parse_pepper_html(html_text, site_info, keyword):
    """
    Parse Pepper network search result HTML page.
    Tries multiple extraction methods:
    1. __NEXT_DATA__ JSON (Pepper sites use Next.js)
    2. JSON-LD structured data
    3. Regex fallback
    """
    posts = []

    # Method 1: __NEXT_DATA__ (Pepper sites are built with Next.js)
    nextdata_match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html_text,
        re.DOTALL,
    )
    if nextdata_match:
        try:
            data = json.loads(nextdata_match.group(1).strip())
            posts = _walk_next_data(data, site_info, keyword)
            if posts:
                return posts
        except json.JSONDecodeError:
            pass

    # Method 2: JSON-LD
    jsonld_blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html_text,
        re.DOTALL,
    )
    for jl in jsonld_blocks:
        try:
            data = json.loads(jl.strip())
            if isinstance(data, list):
                for item in data:
                    post = _extract_jsonld_item(item, site_info, keyword)
                    if post:
                        posts.append(post)
            elif isinstance(data, dict):
                post = _extract_jsonld_item(data, site_info, keyword)
                if post:
                    posts.append(post)
        except json.JSONDecodeError:
            continue

    if posts:
        return posts

    # Method 3: Regex extraction
    posts = _extract_regex(html_text, site_info, keyword)
    return posts


def _walk_next_data(data, site_info, keyword, posts=None):
    """Recursively walk Next.js data tree looking for deal articles."""
    if posts is None:
        posts = []

    if isinstance(data, dict):
        # Check if this node looks like a deal/thread
        title = data.get("title", "")
        if title and keyword.lower() in title.lower():
            post = {
                "site": site_info["site"],
                "domain": site_info["domain"],
                "country": site_info["country"],
                "title": str(title),
                "link": str(data.get("url", data.get("dealUrl", data.get("webUrl", "")))),
                "pub_date": str(data.get("publishedAt", data.get("createdAt", ""))),
                "price": str(data.get("price", "")),
                "temperature": str(data.get("temperature", data.get("hot", ""))),
                "votes": str(data.get("voteCount", data.get("likes", ""))),
                "comments_count": str(data.get("commentCount", data.get("comments", ""))),
                "summary": str(data.get("description", ""))[:300],
                "source": "next_data",
            }
            posts.append(post)

        # Recurse into children
        for v in data.values():
            _walk_next_data(v, site_info, keyword, posts)

    elif isinstance(data, list):
        for item in data:
            _walk_next_data(item, site_info, keyword, posts)

    return posts


def _extract_jsonld_item(item, site_info, keyword):
    """Extract deal post from JSON-LD structured data."""
    if not isinstance(item, dict):
        return None

    title = item.get("name", item.get("headline", ""))
    url = item.get("url", "")

    if not title or keyword.lower() not in title.lower():
        return None

    date_published = item.get("datePublished", item.get("dateCreated", ""))
    description = item.get("description", "")

    # Price
    price = ""
    offers = item.get("offers", {})
    if isinstance(offers, dict):
        price = str(offers.get("price", offers.get("lowPrice", "")))
    elif isinstance(offers, list) and offers:
        price = str(offers[0].get("price", ""))

    # Interaction stats
    votes = comments = ""
    interaction = item.get("interactionStatistic", [])
    if isinstance(interaction, list):
        for stat in interaction:
            stat_type = stat.get("interactionType", "")
            count = stat.get("userInteractionCount", 0)
            if "Comment" in stat_type:
                comments = str(count)
            elif "Like" in stat_type or "Vote" in stat_type:
                votes = str(count)
    elif isinstance(interaction, dict):
        count = interaction.get("userInteractionCount", 0)
        comments = str(count)

    return {
        "site": site_info["site"],
        "domain": site_info["domain"],
        "country": site_info["country"],
        "title": title.strip(),
        "link": url,
        "pub_date": date_published,
        "price": price,
        "temperature": "",
        "votes": votes,
        "comments_count": comments,
        "summary": description[:300] if description else "",
        "source": "jsonld",
    }


def _extract_regex(html_text, site_info, keyword):
    """Fallback: Extract deal posts using regex on raw HTML."""
    posts = []
    domain = site_info["domain"]

    patterns = [
        rf'href="(https?://(?:www\.|forums\.)?{re.escape(domain)}/(?:deals|f|node)/[^"]+)"[^>]*>\s*([^<]+)',
        rf'href="(/(?:deals|f|node)/[^"]+)"[^>]*>\s*([^<]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_text, re.IGNORECASE)
        for url, title in matches:
            title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', title)).strip()

            if not title or keyword.lower() not in title.lower():
                continue
            if url.startswith("/"):
                url = f"https://{domain}{url}"
            if any(p["link"] == url for p in posts):
                continue

            posts.append({
                "site": site_info["site"],
                "domain": domain,
                "country": site_info["country"],
                "title": title,
                "link": url,
                "pub_date": "",
                "price": extract_price(title),
                "temperature": "",
                "votes": "",
                "comments_count": "",
                "summary": "",
                "source": "regex",
            })

    return posts


def parse_rss_xml(xml_text, site_info, keyword):
    """Parse RSS XML and filter by keyword."""
    import xml.etree.ElementTree as ET

    posts = []
    if not xml_text:
        return posts

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return posts

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
        "slash": "http://purl.org/rss/1.0/modules/slash/",
    }

    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(".//atom:entry", ns)
        is_atom = True

    for item in items:
        try:
            if is_atom:
                title_el = item.find("atom:title", ns)
                link_el = item.find("atom:link", ns)
                summary_el = item.find("atom:summary", ns) or item.find("atom:content", ns)
                date_el = item.find("atom:published", ns) or item.find("atom:updated", ns)
            else:
                title_el = item.find("title")
                link_el = item.find("link")
                summary_el = item.find("description")
                date_el = item.find("pubDate") or item.find("{http://purl.org/dc/elements/1.1/}date")

            title = title_el.text if title_el is not None and title_el.text else ""
            link = ""
            if link_el is not None:
                if is_atom:
                    link = link_el.get("href", "")
                else:
                    link = link_el.text if link_el.text else ""

            summary = summary_el.text if summary_el is not None and summary_el.text else ""
            pub_date = date_el.text if date_el is not None and date_el.text else ""

            if keyword.lower() not in (title + " " + summary).lower():
                continue

            comments = ""
            comments_el = item.find("{http://purl.org/rss/1.0/modules/slash/}comments")
            if comments_el is not None and comments_el.text:
                comments = comments_el.text

            posts.append({
                "site": site_info["site"],
                "domain": site_info["domain"],
                "country": site_info["country"],
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.strip(),
                "price": extract_price(title) or extract_price(summary),
                "temperature": "",
                "votes": "",
                "comments_count": comments,
                "summary": summary[:500] if summary else "",
                "source": "rss",
            })
        except Exception:
            continue

    return posts


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Pepper Network Deal Scraper - Cloudflare Bypass Edition"
    )
    parser.add_argument("-k", "--keyword", required=True, help="Search keyword (e.g., navimow)")
    parser.add_argument("--strategy", default="auto",
                        choices=["auto", "direct", "browser", "cookie", "cache", "api", "discovery", "all"],
                        help="Bypass strategy: auto (direct→browser→cookie→cache→api→discovery), direct, "
                             "browser, cookie, cache, api (third-party), discovery (generate URLs), all")
    parser.add_argument("-c", "--countries", default="",
                        help="Comma-separated country codes (us,de,uk,fr,es,mx,pl,br,ca,au)")
    parser.add_argument("--output", default="", help="Output file path (default: auto)")
    parser.add_argument("--api-key", default="", help="Third-party scraping API key (ZenRows/ScraperAPI)")
    parser.add_argument("--api-provider", default="zenrows", choices=["zenrows", "scraperapi"],
                        help="API provider for Strategy 4")

    args = parser.parse_args()
    keyword = args.keyword

    # Filter sites by country
    sites = PEPPER_SITES
    if args.countries:
        countries = [c.strip() for c in args.countries.split(",")]
        sites = [s for s in PEPPER_SITES if s["country"] in countries]

    print(f"\n{'═'*60}")
    print(f"  Pepper Network Deal Scraper")
    print(f"  Keyword: {keyword} | Sites: {len(sites)} | Strategy: {args.strategy}")
    print(f"{'═'*60}\n")

    all_posts = []
    strategies_tried = []

    # Strategy 0: Direct RSS with multiple HTTP backends
    if args.strategy in ("auto", "direct", "all"):
        strategies_tried.append("direct")
        posts = scrape_with_direct_rss(keyword, sites)
        all_posts.extend(posts)
        if posts:
            print(f"\n  ✓ Strategy 'direct' found {len(posts)} posts")

    # Strategy 1: undetected-chromedriver
    if args.strategy in ("browser", "all") or (args.strategy == "auto" and not all_posts):
        strategies_tried.append("browser")
        posts = scrape_with_undetected_chromedriver(keyword, sites)
        all_posts.extend(posts)
        if posts:
            print(f"\n  ✓ Strategy 'browser' found {len(posts)} posts")

    # Strategy 2: Manual cookie injection
    if args.strategy in ("cookie", "all") or (args.strategy == "auto" and not all_posts):
        strategies_tried.append("cookie")
        posts = scrape_with_cookies(keyword, sites)
        all_posts.extend(posts)
        if posts:
            print(f"\n  ✓ Strategy 'cookie' found {len(posts)} posts")

    # Strategy 3: Google cache
    if args.strategy in ("cache", "all") or (args.strategy == "auto" and not all_posts):
        strategies_tried.append("cache")
        posts = scrape_with_google_cache(keyword, sites)
        all_posts.extend(posts)
        if posts:
            print(f"\n  ✓ Strategy 'cache' found {len(posts)} posts")

    # Strategy 4: Third-party API
    if args.strategy in ("api", "all") or (args.strategy == "auto" and not all_posts):
        strategies_tried.append("api")
        posts = scrape_with_api(keyword, sites, api_key=args.api_key, api_provider=args.api_provider)
        all_posts.extend(posts)
        if posts:
            print(f"\n  ✓ Strategy 'api' found {len(posts)} posts")

    # Strategy 5: WebSearch discovery (always run as fallback)
    if args.strategy in ("discovery", "all") or (args.strategy == "auto" and not all_posts):
        strategies_tried.append("discovery")
        posts = scrape_with_websearch_discovery(keyword, sites)
        all_posts.extend(posts)

    # ── Output ─────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  RESULTS")
    print(f"{'═'*60}")
    print(f"  Strategies tried: {', '.join(strategies_tried)}")
    print(f"  Total posts found: {len(all_posts)}")
    print(f"  Sites with results: {len(set(p['site'] for p in all_posts))}/{len(sites)}")

    if all_posts:
        print(f"\n{'─'*60}")
        for i, post in enumerate(all_posts, 1):
            print(f"\n  #{i}")
            print(f"  Site:      {post['site']} ({post['country'].upper()})")
            print(f"  Title:     {post['title']}")
            print(f"  Price:     {post.get('price', '—')}")
            print(f"  Temp:      {post.get('temperature', '—')}°")
            print(f"  Votes:     {post.get('votes', '—')}")
            print(f"  Comments:  {post.get('comments_count', '—')}")
            print(f"  Date:      {post.get('pub_date', '—')}")
            print(f"  Link:      {post['link']}")
            print(f"  Source:    {post.get('source', '—')}")

    # Save JSON
    output_path = args.output or os.path.join(OUTPUT_DIR, f"pepper_{keyword}_results.json")
    output = {
        "keyword": keyword,
        "scan_date": datetime.now().isoformat(),
        "strategies_tried": strategies_tried,
        "total_sites": len(sites),
        "total_posts": len(all_posts),
        "posts": all_posts,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Results saved to: {output_path}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
