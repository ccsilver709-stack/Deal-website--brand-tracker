#!/usr/bin/env python3
"""
ScraperAPI Deal Site Scraper - Strategy 4 (Recommended for Cloudflare sites)

Uses ScraperAPI's proxy network + JS rendering to bypass Cloudflare Managed Challenge.
This is the most reliable strategy for Pepper network sites (Slickdeals, MyDealz,
HotUKDeals, Dealabs, Chollometro, etc.) that use Cloudflare's highest protection level.

Key advantages:
- No Chrome/browser required
- No undetected-chromedriver needed
- Uses urllib (standard library, no pip install needed)
- 5000 free API requests/month (https://www.scraperapi.com/signup/)

Usage:
    python scraperapi_scraper.py -k anker --api-key YOUR_KEY
    python scraperapi_scraper.py -k anker --api-key YOUR_KEY -c us,de,uk
    python scraperapi_scraper.py -k "robot lawn mower" --api-key YOUR_KEY --output results.json
    python scraperapi_scraper.py -k anker --api-key YOUR_KEY --full-mode

Note: The requests library has SSL compatibility issues with ScraperAPI on some
systems. This script uses urllib (standard library) with a relaxed SSL context
to avoid this problem.
"""

import argparse
import json
import re
import time
import html
import ssl
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# Relaxed SSL context (avoids SSLEOFError with ScraperAPI on some Python builds)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

CN_TZ = timezone(timedelta(hours=8))

# All deal sites covered by the skill
SITES = [
    # Pepper network
    {"site": "Slickdeals", "country": "us", "cc": "us",
     "rss": "https://slickdeals.net/rss/search?q={q}",
     "html": "https://slickdeals.net/search?q={q}&sort=newest"},
    {"site": "MyDealz", "country": "de", "cc": "de",
     "rss": "https://www.mydealz.de/rss/search?q={q}",
     "html": "https://www.mydealz.de/search?q={q}"},
    {"site": "HotUKDeals", "country": "uk", "cc": "gb",
     "rss": "https://www.hotukdeals.com/rss/search?q={q}",
     "html": "https://www.hotukdeals.com/search?q={q}"},
    {"site": "Dealabs", "country": "fr", "cc": "fr",
     "rss": "https://www.dealabs.com/rss/search?q={q}",
     "html": "https://www.dealabs.com/search?q={q}"},
    {"site": "Chollometro", "country": "es", "cc": "es",
     "rss": "https://www.chollometro.com/rss/search?q={q}",
     "html": "https://www.chollometro.com/search?q={q}"},
    {"site": "Promodescuentos", "country": "mx", "cc": "mx",
     "rss": "https://www.promodescuentos.com/rss/search?q={q}",
     "html": "https://www.promodescuentos.com/search?q={q}"},
    {"site": "Pepper.pl", "country": "pl", "cc": "pl",
     "rss": "https://www.pepper.pl/rss/search?q={q}",
     "html": "https://www.pepper.pl/search?q={q}"},
    {"site": "Pelando", "country": "br", "cc": "br",
     "rss": "https://www.pelando.com.br/rss/search?q={q}",
     "html": "https://www.pelando.com.br/search?q={q}"},
    {"site": "Promobit", "country": "br", "cc": "br",
     "rss": "https://www.promobit.com.br/rss/search?q={q}",
     "html": "https://www.promobit.com.br/search?q={q}"},
    # Independent sites
    {"site": "RedFlagDeals", "country": "ca", "cc": "ca",
     "rss": None,
     "html": "https://forums.redflagdeals.com/search/?q={q}"},
    {"site": "OzBargain", "country": "au", "cc": "au",
     "rss": "https://www.ozbargain.com.au/rss/search?q={q}",
     "html": "https://www.ozbargain.com.au/search?q={q}"},
]


class ScraperResponse:
    """Response wrapper mimicking requests.Response for urllib."""
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def fetch_via_scraperapi(url, api_key, render=True, country_code=None, timeout=30, no_retry=False):
    """Fetch a URL via ScraperAPI. No retry on 404. Single attempt in fast mode."""
    params = {"api_key": api_key, "url": url, "render": str(render).lower()}
    if country_code:
        params["country_code"] = country_code
    api_url = "https://api.scraperapi.com/?" + urllib.parse.urlencode(params)

    max_attempts = 1 if no_retry else 2
    for attempt in range(max_attempts):
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return ScraperResponse(resp.status, body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ScraperResponse(404, "")
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            else:
                return ScraperResponse(e.code, "")
        except Exception:
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            else:
                raise


def extract_price(text):
    patterns = [
        r'[\$£€]\s?\d+[.,]?\d{0,2}',
        r'R\$\s?\d+[.,]\d{1,2}',
        r'\d+[.,]\d{2}\s?(?:€|zł|PLN)',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(0)
    return ""


def extract_metrics(html_context):
    """Extract heat/temperature, votes, and comments from HTML context."""
    heat = 0
    votes = 0
    comments = 0

    heat_patterns = [
        r'(\d{1,4})\s*°',
        r'temperature[^>]*>\s*(\d{1,4})',
        r'cept-temperature[^>]*>\s*(\d{1,4})',
        r'"temperature"\s*:\s*(\d{1,4})',
        r'"degree"\s*:\s*(\d{1,4})',
        r'data-temp(?:erature)?="(\d{1,4})"',
        r'(\d{1,4})\s*(?:grad|grados?)',
        r'\+(\d{1,4})\s*(?:point|vote|degree)',
        r'data-votes="(\d{1,4})"',
        r'"score"\s*:\s*(\d{1,4})',
        r'"rating"\s*:\s*(\d{1,4})',
    ]
    for p in heat_patterns:
        m = re.search(p, html_context, re.I)
        if m:
            heat = max(heat, int(m.group(1)))

    vote_patterns = [
        r'(\d{1,6})\s*(?:upvotes?|likes?|👍)',
        r'(\d{1,6})\s*(?:votos?|stimmen)',
    ]
    for p in vote_patterns:
        m = re.search(p, html_context, re.I)
        if m:
            votes = max(votes, int(m.group(1)))

    comment_patterns = [
        r'(\d{1,6})\s*(?:comments?|Kommentare?|commentaires?|comentarios?)',
        r'"commentCount"\s*:\s*(\d{1,6})',
        r'"comments"\s*:\s*(\d{1,6})',
        r'(\d{1,6})\s*(?:reply|replies|Respuestas?)',
        r'href="[^"]*#comment[^"]*"[^>]*>\s*(\d{1,6})',
        r'data-replies="(\d{1,6})"',
        r'data-comments="(\d{1,6})"',
        r'data-c="(\d{1,6})"',
    ]
    for p in comment_patterns:
        m = re.search(p, html_context, re.I)
        if m:
            comments = max(comments, int(m.group(1)))

    return heat, votes, comments


def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return None


def parse_rss(xml_text, site_info, keyword):
    """Parse RSS XML and extract posts matching keyword."""
    posts = []
    try:
        xml_clean = re.sub(r'<\?xml[^>]*\?>', '', xml_text, count=1)
        root = ET.fromstring(xml_clean)
    except ET.ParseError:
        return parse_rss_regex(xml_text, site_info, keyword)

    items = root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry')
    for item in items:
        title = link = pub_date = desc = ""
        t = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
        if t is not None and t.text:
            title = t.text.strip()
        l = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
        if l is not None:
            link = l.text.strip() if l.text else l.get('href', '')
        d = item.find('pubDate') or item.find('{http://www.w3.org/2005/Atom}published') or item.find('{http://www.w3.org/2005/Atom}updated')
        if d is not None and d.text:
            pub_date = d.text.strip()
        de = item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary')
        if de is not None and de.text:
            desc = re.sub(r'<[^>]+>', '', de.text).strip()

        if keyword.lower() in (title + " " + desc).lower():
            dt = parse_date(pub_date)
            heat, votes, comments = extract_metrics(desc)
            posts.append({
                "site": site_info["site"], "country": site_info["country"],
                "title": title, "link": link, "pub_date": pub_date,
                "pub_date_parsed": dt.strftime('%Y-%m-%d %H:%M %Z') if dt else "",
                "price": extract_price(title + " " + desc),
                "heat": heat, "votes": votes, "comments": comments,
                "summary": desc[:300], "source": "scraperapi_rss",
            })
    return posts


def parse_rss_regex(text, site_info, keyword):
    posts = []
    blocks = re.findall(r'<(?:item|entry)[^>]*>(.*?)</(?:item|entry)>', text, re.DOTALL)
    for block in blocks:
        title_m = re.search(r'<title[^>]*>(.*?)</title>', block, re.DOTALL)
        link_m = re.search(r'<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>|<link[^>]*href="([^"]*)"', block, re.DOTALL)
        date_m = re.search(r'<(?:pubDate|published|updated)[^>]*>(.*?)</(?:pubDate|published|updated)>', block, re.DOTALL)
        desc_m = re.search(r'<(?:description|summary|content)[^>]*>(.*?)</(?:description|summary|content)>', block, re.DOTALL)
        title = html.unescape(title_m.group(1).strip()) if title_m else ""
        link = ""
        if link_m:
            link = (link_m.group(1) or link_m.group(2) or "").strip()
        pub_date = date_m.group(1).strip() if date_m else ""
        desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""
        desc = html.unescape(desc)
        if keyword.lower() in (title + " " + desc).lower():
            heat, votes, comments = extract_metrics(desc)
            posts.append({
                "site": site_info["site"], "country": site_info["country"],
                "title": title, "link": link, "pub_date": pub_date,
                "pub_date_parsed": "", "price": extract_price(title + " " + desc),
                "heat": heat, "votes": votes, "comments": comments,
                "summary": desc[:300], "source": "scraperapi_rss_regex",
            })
    return posts


def parse_html(page_source, site_info, keyword):
    """Extract deal links from HTML page source."""
    posts = []
    anchor_pattern = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
    seen = set()
    for m in anchor_pattern.finditer(page_source):
        href = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        text = html.unescape(text)
        if keyword.lower() in text.lower() and len(text) > 10 and href not in seen:
            seen.add(href)
            base = site_info["html"].split("/search")[0].rsplit("/", 2)[0]
            full_link = href if href.startswith("http") else base + href if href.startswith("/") else base + "/" + href

            ctx_start = max(0, m.start() - 1200)
            ctx_end = min(len(page_source), m.end() + 1200)
            context = page_source[ctx_start:ctx_end]
            heat, votes, comments = extract_metrics(context)

            posts.append({
                "site": site_info["site"], "country": site_info["country"],
                "title": text[:200], "link": full_link, "pub_date": "",
                "pub_date_parsed": "", "price": extract_price(text),
                "heat": heat, "votes": votes, "comments": comments,
                "summary": "", "source": "scraperapi_html",
            })
    return posts


def process_site(site, keyword, api_key, timeout=30, full_mode=False):
    """Process a single site with optimized strategy.

    FAST MODE (default):
      1. Try RSS (render=false, ~3-5 sec) — no retry
      2. If RSS fails, try HTML (render=false, ~5-8 sec) — no retry
      3. STOP — don't fall through to render=true (that's 20-30 sec)

    FULL MODE (--full-mode):
      1. Try RSS (render=false) — no retry, gets basic data
      2. If RSS fails, go straight to HTML (render=true, ~15-20 sec) — gets heat
      3. Skip render=false entirely (saves one request)
    """
    q = urllib.parse.quote(keyword)
    posts = []

    # 1. Try RSS first (render=false — RSS is XML, no JS needed, very fast)
    if site.get("rss"):
        try:
            resp = fetch_via_scraperapi(
                site["rss"].format(q=q), api_key,
                render=False, country_code=site.get("cc"),
                timeout=timeout, no_retry=True  # Single attempt, no retry
            )
            if resp.status_code == 200 and ("<item" in resp.text or "<rss" in resp.text):
                posts = parse_rss(resp.text, site, keyword)
                if not posts:
                    posts = parse_rss_regex(resp.text, site, keyword)
                if posts:
                    return site, posts, f"[{site['country'].upper()}] {site['site']} (RSS) → {len(posts)} posts"
        except Exception:
            pass

    # 2. HTML fallback
    if site.get("html"):
        # Full mode: skip render=false, go straight to render=true for heat data
        # Fast mode: try render=false first (much faster)
        use_render = True if full_mode else False

        try:
            resp = fetch_via_scraperapi(
                site["html"].format(q=q), api_key,
                render=use_render, country_code=site.get("cc"),
                timeout=timeout, no_retry=True  # Single attempt
            )
            if resp.status_code == 200:
                if "just a moment" in resp.text.lower() or "请稍候" in resp.text:
                    # Cloudflare blocked even with render — give up this site
                    return site, [], f"[{site['country'].upper()}] {site['site']} BLOCKED"
                posts = parse_html(resp.text, site, keyword)
                tag = "HTML-render" if use_render else "HTML-fast"
                return site, posts, f"[{site['country'].upper()}] {site['site']} ({tag}) → {len(posts)} posts"
            else:
                return site, [], f"[{site['country'].upper()}] {site['site']} HTTP {resp.status_code}"
        except Exception as e:
            return site, [], f"[{site['country'].upper()}] {site['site']} ERROR: {str(e)[:50]}"

    return site, [], f"[{site['country'].upper()}] {site['site']} SKIP (no URL)"


def main():
    parser = argparse.ArgumentParser(description="ScraperAPI Deal Site Scraper (Strategy 4)")
    parser.add_argument("-k", "--keyword", required=True, help="Search keyword (e.g., anker)")
    parser.add_argument("--api-key", required=True, help="ScraperAPI API key")
    parser.add_argument("-c", "--countries", default="", help="Comma-separated country codes")
    parser.add_argument("--output", default="", help="Output file path")
    parser.add_argument("--timeout", type=int, default=30, help="Per-request timeout in seconds")
    parser.add_argument("--full-mode", action="store_true", help="Enable JS rendering for heat data (slower)")
    args = parser.parse_args()

    keyword = args.keyword
    country_filter = [c.strip() for c in args.countries.split(",")] if args.countries else None
    sites = [s for s in SITES if not country_filter or s["country"] in country_filter]

    mode_label = "FULL (with heat)" if args.full_mode else "FAST (no heat)"
    print(f"ScraperAPI Scraper: keyword='{keyword}', {len(sites)} sites, mode={mode_label}", flush=True)
    print(f"API Key: {args.api_key[:8]}...{args.api_key[-4:]}", flush=True)

    # Parallel fetch all sites — use more workers for better concurrency
    max_workers = min(len(sites), 12)  # Up from 6 to 12
    print(f"Fetching {len(sites)} sites in parallel (max_workers={max_workers})...", flush=True)
    print(f"Timeout per request: {args.timeout}s | Retry: disabled (single attempt)", flush=True)
    print(f"Strategy: {'RSS→HTML(render=true)' if args.full_mode else 'RSS→HTML(render=false)'}", flush=True)
    print(flush=True)

    all_posts = []
    logs = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_site, site, keyword, args.api_key, args.timeout, args.full_mode): site
            for site in sites
        }
        for future in as_completed(futures):
            site, posts, msg = future.result()
            elapsed = time.time() - start_time
            print(f"  [{elapsed:5.1f}s] {msg}", flush=True)
            logs.append(msg)
            all_posts.extend(posts)

    elapsed_total = time.time() - start_time

    # Save results
    output_path = args.output or f"scraperapi_{keyword}_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "keyword": keyword,
            "total_posts": len(all_posts),
            "posts": all_posts,
            "elapsed_seconds": round(elapsed_total, 1),
            "mode": "full" if args.full_mode else "fast"
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Total: {len(all_posts)} posts in {elapsed_total:.1f}s ({mode_label})")
    print(f"Saved to: {output_path}")
    for i, p in enumerate(all_posts, 1):
        print(f"  #{i} {p['site']} ({p['country']}) - {p['title'][:80]}")


if __name__ == "__main__":
    main()
