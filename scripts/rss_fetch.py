#!/usr/bin/env python3
"""
Deal Site RSS Batch Fetcher

Scans 60+ deal sites across 11+ countries via RSS/Atom feeds.
Pure Python standard library — no required dependencies.
Optional: requests, cloudscraper, curl_cffi for enhanced anti-bot bypass.

Usage:
  python rss_fetch.py -k "navimow"
  python rss_fetch.py -k anker -k soundcore -c us,de,uk --search-fallback
  python rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16
  python rss_fetch.py -k anker --output csv --workers 15
  python rss_fetch.py -k "robot lawn mower" --timeout 15
"""

import argparse
import csv
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════════
#  Deal Sites Configuration (60+ sites, 11+ countries)
# ═══════════════════════════════════════════════════════════════════════

DEAL_SITES = [
    # ── Pepper Network (Cloudflare protected, but some allow RSS) ──
    {"country": "us", "site": "Slickdeals", "domain": "slickdeals.net",
     "rss_url": "https://slickdeals.net/rss/search?q={q}",
     "search_url": "https://slickdeals.net/search?q={q}",
     "pepper": True},
    {"country": "de", "site": "MyDealz", "domain": "mydealz.de",
     "rss_url": "https://www.mydealz.de/rss/search?q={q}",
     "search_url": "https://www.mydealz.de/search?q={q}",
     "pepper": True},
    {"country": "uk", "site": "HotUKDeals", "domain": "hotukdeals.com",
     "rss_url": "https://www.hotukdeals.com/rss/search?q={q}",
     "search_url": "https://www.hotukdeals.com/search?q={q}",
     "pepper": True},
    {"country": "fr", "site": "Dealabs", "domain": "dealabs.com",
     "rss_url": "https://www.dealabs.com/rss/search?q={q}",
     "search_url": "https://www.dealabs.com/search?q={q}",
     "pepper": True},
    {"country": "es", "site": "Chollometro", "domain": "chollometro.com",
     "rss_url": "https://www.chollometro.com/rss/search?q={q}",
     "search_url": "https://www.chollometro.com/search?q={q}",
     "pepper": True},
    {"country": "mx", "site": "Promodescuentos", "domain": "promodescuentos.com",
     "rss_url": "https://www.promodescuentos.com/rss/search?q={q}",
     "search_url": "https://www.promodescuentos.com/search?q={q}",
     "pepper": True},
    {"country": "pl", "site": "Pepper.pl", "domain": "pepper.pl",
     "rss_url": "https://www.pepper.pl/rss/search?q={q}",
     "search_url": "https://www.pepper.pl/search?q={q}",
     "pepper": True},
    {"country": "br", "site": "Pelando", "domain": "pelando.com.br",
     "rss_url": "https://www.pelando.com.br/rss/search?q={q}",
     "search_url": "https://www.pelando.com.br/search?q={q}",
     "pepper": True},
    {"country": "br", "site": "Promobit", "domain": "promobit.com.br",
     "rss_url": "https://www.promobit.com.br/rss/search?q={q}",
     "search_url": "https://www.promobit.com.br/search?q={q}",
     "pepper": True},
    {"country": "ca", "site": "RedFlagDeals", "domain": "redflagdeals.com",
     "rss_url": "https://forums.redflagdeals.com/rss/",
     "search_url": "https://forums.redflagdeals.com/search/?q={q}",
     "pepper": True},
    {"country": "au", "site": "OzBargain", "domain": "ozbargain.com.au",
     "rss_url": "https://www.ozbargain.com.au/rss.xml",
     "search_url": "https://www.ozbargain.com.au/search?q={q}",
     "pepper": True},

    # ── US Non-Pepper ──
    {"country": "us", "site": "DealNews", "domain": "dealnews.com",
     "rss_url": "https://www.dealnews.com/rss.xml",
     "search_url": "https://www.dealnews.com/search/{q}.html", "pepper": False},
    {"country": "us", "site": "Reddit r/deals", "domain": "reddit.com",
     "rss_url": "https://www.reddit.com/r/deals/.rss",
     "search_url": "https://www.reddit.com/r/deals/search/?q={q}", "pepper": False},
    {"country": "us", "site": "Hip2Save", "domain": "hip2save.com",
     "rss_url": "https://hip2save.com/feed/",
     "search_url": "https://hip2save.com/?s={q}", "pepper": False},
    {"country": "us", "site": "DansDeals", "domain": "dansdeals.com",
     "rss_url": "https://www.dansdeals.com/feed/",
     "search_url": "https://www.dansdeals.com/?s={q}", "pepper": False},
    {"country": "us", "site": "TechBargains", "domain": "techbargains.com",
     "rss_url": "https://www.techbargains.com/rss.xml",
     "search_url": "https://www.techbargains.com/search?q={q}", "pepper": False},
    {"country": "us", "site": "BensBargains", "domain": "bensbargains.com",
     "rss_url": "https://bensbargains.com/feed/",
     "search_url": "https://bensbargains.com/?s={q}", "pepper": False},
    {"country": "us", "site": "DealsPlus", "domain": "dealsplus.com",
     "rss_url": "https://www.dealsplus.com/rss",
     "search_url": "https://www.dealsplus.com/search?q={q}", "pepper": False},
    {"country": "us", "site": "DealCatcher", "domain": "dealcatcher.com",
     "rss_url": "https://www.dealcatcher.com/rss",
     "search_url": "https://www.dealcatcher.com/search?q={q}", "pepper": False},
    {"country": "us", "site": "Dealighted", "domain": "dealighted.com",
     "rss_url": "https://www.dealighted.com/rss/popular",
     "search_url": "https://www.dealighted.com/search?q={q}", "pepper": False},
    {"country": "us", "site": "BradsDeals", "domain": "bradsdeals.com",
     "rss_url": "https://www.bradsdeals.com/rss",
     "search_url": "https://www.bradsdeals.com/search?q={q}", "pepper": False},
    {"country": "us", "site": "1Sale", "domain": "1sale.com",
     "rss_url": "https://www.1sale.com/feed/",
     "search_url": "https://www.1sale.com/?s={q}", "pepper": False},
    {"country": "us", "site": "Reddit r/buildapcsales", "domain": "reddit.com",
     "rss_url": "https://www.reddit.com/r/buildapcsales/.rss",
     "search_url": "https://www.reddit.com/r/buildapcsales/search/?q={q}", "pepper": False},
    {"country": "us", "site": "Reddit r/GameDeals", "domain": "reddit.com",
     "rss_url": "https://www.reddit.com/r/GameDeals/.rss",
     "search_url": "https://www.reddit.com/r/GameDeals/search/?q={q}", "pepper": False},
    {"country": "us", "site": "DealMoon", "domain": "dealmoon.com",
     "rss_url": "https://dealmoon.com/rss",
     "search_url": "https://dealmoon.com/search?q={q}", "pepper": False},

    # ── Canada ──
    {"country": "ca", "site": "SaveaLoonie", "domain": "savealoonie.com",
     "rss_url": "https://www.savealoonie.com/feed/",
     "search_url": "https://www.savealoonie.com/?s={q}", "pepper": False},
    {"country": "ca", "site": "SmartCanucks", "domain": "smartcanucks.ca",
     "rss_url": "https://www.smartcanucks.ca/feed/",
     "search_url": "https://www.smartcanucks.ca/?s={q}", "pepper": False},

    # ── Germany ──
    {"country": "de", "site": "Mein-Deal", "domain": "mein-deal.com",
     "rss_url": "https://www.mein-deal.com/feed/",
     "search_url": "https://www.mein-deal.com/?s={q}", "pepper": False},
    {"country": "de", "site": "Dealgott", "domain": "dealgott.de",
     "rss_url": "https://www.dealgott.de/feed/",
     "search_url": "https://www.dealgott.de/?s={q}", "pepper": False},
    {"country": "de", "site": "DealDoktor", "domain": "dealdoktor.de",
     "rss_url": "https://www.dealdoktor.de/feed/",
     "search_url": "https://www.dealdoktor.de/?s={q}", "pepper": False},
    {"country": "de", "site": "Sparwelt", "domain": "sparwelt.de",
     "rss_url": "https://www.sparwelt.de/rss/feed",
     "search_url": "https://www.sparwelt.de/search?q={q}", "pepper": False},

    # ── UK ──
    {"country": "uk", "site": "LatestDeals", "domain": "latestdeals.co.uk",
     "rss_url": "https://www.latestdeals.co.uk/feeds/rss",
     "search_url": "https://www.latestdeals.co.uk/deals?q={q}", "pepper": False},
    {"country": "uk", "site": "DealSpy", "domain": "dealspy.co.uk",
     "rss_url": "https://dealspy.co.uk/feed/",
     "search_url": "https://dealspy.co.uk/?s={q}", "pepper": False},

    # ── France ──
    {"country": "fr", "site": "SerialDealer", "domain": "serialdealer.fr",
     "rss_url": "https://www.serialdealer.fr/feed/",
     "search_url": "https://www.serialdealer.fr/?s={q}", "pepper": False},
    {"country": "fr", "site": "Bons-Plans-Geeks", "domain": "bons-plans-geeks.com",
     "rss_url": "https://www.bons-plans-geeks.com/feed/",
     "search_url": "https://www.bons-plans-geeks.com/?s={q}", "pepper": False},

    # ── Italy ──
    {"country": "it", "site": "Scontify", "domain": "scontify.com",
     "rss_url": "https://www.scontify.com/feed/",
     "search_url": "https://www.scontify.com/?s={q}", "pepper": False},
    {"country": "it", "site": "WikiDeal", "domain": "wikideal.it",
     "rss_url": "https://www.wikideal.it/feed/",
     "search_url": "https://www.wikideal.it/?s={q}", "pepper": False},

    # ── Spain ──
    {"country": "es", "site": "SuperChollos", "domain": "superchollos.com",
     "rss_url": "https://www.superchollos.com/feed/",
     "search_url": "https://www.superchollos.com/?s={q}", "pepper": False},

    # ── Mexico ──
    {"country": "mx", "site": "Megadescuentos", "domain": "megadescuentos.com",
     "rss_url": "https://www.megadescuentos.com/feed/",
     "search_url": "https://www.megadescuentos.com/?s={q}", "pepper": False},

    # ── Brazil ──
    {"country": "br", "site": "Gatry", "domain": "gatry.com",
     "rss_url": "https://www.gatry.com/feed/",
     "search_url": "https://www.gatry.com/search?q={q}", "pepper": False},

    # ── India ──
    {"country": "in", "site": "FreeKaaMaal", "domain": "freekaamaal.com",
     "rss_url": "https://www.freekaamaal.com/feed/",
     "search_url": "https://www.freekaamaal.com/?s={q}", "pepper": False},
    {"country": "in", "site": "IndiaBargains", "domain": "indiabargains.com",
     "rss_url": "https://www.indiabargains.com/feed/",
     "search_url": "https://www.indiabargains.com/?s={q}", "pepper": False},

    # ── Netherlands ──
    {"country": "nl", "site": "Kortingscode", "domain": "kortingscode.nl",
     "rss_url": "https://www.kortingscode.nl/feed/",
     "search_url": "https://www.kortingscode.nl/?s={q}", "pepper": False},
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# SSL context that doesn't verify (some deal sites have cert issues)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ═══════════════════════════════════════════════════════════════════════
#  HTTP Fetching (multi-backend with fallback)
# ═══════════════════════════════════════════════════════════════════════

def fetch_url(url, timeout=10):
    """
    Fetch URL content with multiple HTTP backends.
    Tries: urllib → cloudscraper → curl_cffi → requests
    Returns (content_str, backend_used) or (None, error_msg).
    """
    # Backend 1: urllib (always available)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        if content and "Just a moment" not in content:
            return content, "urllib"
    except Exception:
        pass

    # Backend 2: cloudscraper (anti-bot bypass)
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=timeout)
        if resp.status_code == 200 and "Just a moment" not in resp.text:
            return resp.text, "cloudscraper"
    except Exception:
        pass

    # Backend 3: curl_cffi (TLS fingerprint simulation)
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(url, timeout=timeout,
                                 impersonate="chrome",
                                 headers={"User-Agent": UA})
        if resp.status_code == 200 and "Just a moment" not in resp.text:
            return resp.text, "curl_cffi"
    except Exception:
        pass

    # Backend 4: requests (if installed)
    try:
        import requests
        resp = requests.get(url, timeout=timeout,
                            headers={"User-Agent": UA},
                            verify=False)
        if resp.status_code == 200 and "Just a moment" not in resp.text:
            return resp.text, "requests"
    except Exception:
        pass

    return None, "all backends failed"


# ═══════════════════════════════════════════════════════════════════════
#  RSS/Atom Parsing
# ═══════════════════════════════════════════════════════════════════════

def extract_price(text):
    """Extract price from text using regex."""
    if not text:
        return ""
    patterns = [
        r'[\$£€¥₹]\s?(\d{1,}(?:[.,]\d{2})?)',
        r'(\d{1,}(?:[.,]\d{2})?)\s?[\$£€¥₹]',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def parse_rss(xml_text, site_info, keywords):
    """
    Parse RSS/Atom XML and filter by keywords.
    Returns list of post dicts.
    """
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
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    # Try RSS items first, then Atom entries
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

            summary = ""
            if summary_el is not None and summary_el.text:
                summary = summary_el.text
            pub_date = date_el.text if date_el is not None and date_el.text else ""

            # Keyword filtering (OR match — any keyword hits)
            combined = (title + " " + summary).lower()
            if not any(kw.lower() in combined for kw in keywords):
                continue

            # Extract comments count (WordPress slash module)
            comments = ""
            comments_el = item.find("{http://purl.org/rss/1.0/modules/slash/}comments")
            if comments_el is not None and comments_el.text:
                comments = comments_el.text

            # Determine if browser is needed for interaction data
            needs_browser = site_info.get("pepper", False)

            posts.append({
                "site": site_info["site"],
                "domain": site_info["domain"],
                "country": site_info["country"],
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.strip(),
                "summary": summary[:500] if summary else "",
                "price": extract_price(title) or extract_price(summary),
                "temperature": "",
                "votes": "",
                "comments_count": comments,
                "needs_browser": needs_browser,
            })
        except Exception:
            continue

    return posts


# ═══════════════════════════════════════════════════════════════════════
#  Search Engine Fallback
# ═══════════════════════════════════════════════════════════════════════

def search_google(site_domain, keywords, num=10):
    """Search Google for site:domain + keywords. Returns list of (title, url)."""
    query = f"site:{site_domain} " + " OR ".join(keywords)
    google_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={num}"

    content, backend = fetch_url(google_url, timeout=15)
    if not content:
        return []

    results = []
    # Extract URLs from Google results
    escaped = re.escape(site_domain)
    url_pattern = rf'https?://(?:www\.)?{escaped}/[^\s"\'<>]+'
    found_urls = re.findall(url_pattern, content)

    # Extract titles from <h3> tags
    title_pattern = r'<h3[^>]*>(.*?)</h3>'
    titles = re.findall(title_pattern, content, re.DOTALL)
    titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]

    seen = set()
    for i, url in enumerate(found_urls[:num]):
        if url in seen:
            continue
        seen.add(url)
        title = titles[i] if i < len(titles) else ""
        results.append((title, url))

    return results


def search_bing(site_domain, keywords, num=10):
    """Search Bing for site:domain + keywords. Returns list of (title, url)."""
    query = f"site:{site_domain} " + " OR ".join(keywords)
    bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={num}"

    content, backend = fetch_url(bing_url, timeout=15)
    if not content:
        return []

    results = []
    escaped = re.escape(site_domain)
    url_pattern = rf'https?://(?:www\.)?{escaped}/[^\s"\'<>]+'
    found_urls = re.findall(url_pattern, content)

    title_pattern = r'<h2[^>]*><a[^>]*>(.*?)</a>'
    titles = re.findall(title_pattern, content, re.DOTALL)
    titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]

    seen = set()
    for i, url in enumerate(found_urls[:num]):
        if url in seen:
            continue
        seen.add(url)
        title = titles[i] if i < len(titles) else ""
        results.append((title, url))

    return results


def search_google_news(site_domain, keywords, date_from, date_to, num=10):
    """Search Google News with date range for site:domain + keywords."""
    query = f"site:{site_domain} " + " OR ".join(keywords)
    # Google News search with date range
    google_url = (
        f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        f"&tbm=nws&num={num}"
    )
    if date_from and date_to:
        # tbs=cdr:1,cd_min:M/D/Y,cd_max:M/D/Y
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d")
            d_to = datetime.strptime(date_to, "%Y-%m-%d")
            tbs = f"cdr:1,cd_min:{d_from.month}/{d_from.day}/{d_from.year},cd_max:{d_to.month}/{d_to.day}/{d_to.year}"
            google_url += f"&tbs={urllib.parse.quote(tbs)}"
        except ValueError:
            pass

    content, backend = fetch_url(google_url, timeout=15)
    if not content:
        return []

    results = []
    escaped = re.escape(site_domain)
    url_pattern = rf'https?://(?:www\.)?{escaped}/[^\s"\'<>]+'
    found_urls = re.findall(url_pattern, content)

    title_pattern = r'<h3[^>]*>(.*?)</h3>'
    titles = re.findall(title_pattern, content, re.DOTALL)
    titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]

    seen = set()
    for i, url in enumerate(found_urls[:num]):
        if url in seen:
            continue
        seen.add(url)
        title = titles[i] if i < len(titles) else ""
        results.append((title, url))

    return results


# ═══════════════════════════════════════════════════════════════════════
#  Site Fetcher (single site)
# ═══════════════════════════════════════════════════════════════════════

def fetch_site(site_info, keywords, timeout, search_fallback, date_from, date_to):
    """
    Fetch deals from a single site.
    Returns (site_info, posts, source, error).
    """
    # Format RSS URL with first keyword
    rss_url = site_info["rss_url"].format(
        q=urllib.parse.quote(keywords[0]) if keywords else ""
    )

    # Try RSS first
    content, backend = fetch_url(rss_url, timeout=timeout)

    if content:
        posts = parse_rss(content, site_info, keywords)
        if posts:
            for p in posts:
                p["source"] = "rss"
            return site_info, posts, f"rss ({backend})", None

    # RSS failed or no matches — try search fallback
    if search_fallback:
        results = search_google(site_info["domain"], keywords)
        if results:
            posts = []
            for title, url in results:
                combined = (title + " " + url).lower()
                if any(kw.lower() in combined for kw in keywords):
                    posts.append({
                        "site": site_info["site"],
                        "domain": site_info["domain"],
                        "country": site_info["country"],
                        "title": title,
                        "link": url,
                        "pub_date": "",
                        "summary": "",
                        "price": extract_price(title),
                        "temperature": "",
                        "votes": "",
                        "comments_count": "",
                        "needs_browser": site_info.get("pepper", False),
                        "source": "google_fallback",
                    })
            if posts:
                return site_info, posts, "google_fallback", None

    # Try date-range search if specified
    if date_from and date_to:
        results = search_google_news(site_info["domain"], keywords, date_from, date_to)
        if results:
            posts = []
            for title, url in results:
                combined = (title + " " + url).lower()
                if any(kw.lower() in combined for kw in keywords):
                    posts.append({
                        "site": site_info["site"],
                        "domain": site_info["domain"],
                        "country": site_info["country"],
                        "title": title,
                        "link": url,
                        "pub_date": "",
                        "summary": "",
                        "price": extract_price(title),
                        "temperature": "",
                        "votes": "",
                        "comments_count": "",
                        "needs_browser": site_info.get("pepper", False),
                        "source": "date_search_google",
                    })
            if posts:
                return site_info, posts, "date_search_google", None

        # Try Bing as backup
        results = search_bing(site_info["domain"], keywords)
        if results:
            posts = []
            for title, url in results:
                combined = (title + " " + url).lower()
                if any(kw.lower() in combined for kw in keywords):
                    posts.append({
                        "site": site_info["site"],
                        "domain": site_info["domain"],
                        "country": site_info["country"],
                        "title": title,
                        "link": url,
                        "pub_date": "",
                        "summary": "",
                        "price": extract_price(title),
                        "temperature": "",
                        "votes": "",
                        "comments_count": "",
                        "needs_browser": site_info.get("pepper", False),
                        "source": "date_search_bing",
                    })
            if posts:
                return site_info, posts, "date_search_bing", None

    # All methods failed
    error = "RSS failed" if not content else "No keyword matches"
    return site_info, [], "none", error


# ═══════════════════════════════════════════════════════════════════════
#  Output Formatting
# ═══════════════════════════════════════════════════════════════════════

def output_json(all_posts, failed_sites, keywords, scan_date):
    """Generate JSON output."""
    return json.dumps({
        "keyword": " + ".join(keywords),
        "scan_date": scan_date,
        "total_sites": len(DEAL_SITES),
        "total_posts": len(all_posts),
        "posts": all_posts,
        "failed_sites": failed_sites,
    }, ensure_ascii=False, indent=2)


def output_csv(all_posts):
    """Generate CSV output."""
    if not all_posts:
        return ""
    output = io.StringIO()
    fieldnames = ["country", "site", "title", "link", "pub_date",
                  "price", "temperature", "votes", "comments_count",
                  "needs_browser", "source", "summary"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for post in all_posts:
        writer.writerow(post)
    return output.getvalue()


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Deal Site RSS Batch Fetcher — scan 60+ deal sites worldwide"
    )
    parser.add_argument("-k", "--keyword", action="append", required=True,
                        help="Search keyword (can be repeated for OR match)")
    parser.add_argument("-c", "--countries", default="",
                        help="Comma-separated country codes (us,ca,de,uk,fr,it,es,mx,pl,br,au,in,nl)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Per-site request timeout in seconds (default: 10)")
    parser.add_argument("--output", default="json", choices=["json", "csv"],
                        help="Output format (default: json)")
    parser.add_argument("--search-fallback", action="store_true",
                        help="Use Google search fallback for RSS-failed sites")
    parser.add_argument("--workers", type=int, default=10,
                        help="Concurrent workers (default: 10)")
    parser.add_argument("--date-from", default="",
                        help="Date range start (YYYY-MM-DD) for historical search")
    parser.add_argument("--date-to", default="",
                        help="Date range end (YYYY-MM-DD) for historical search")
    parser.add_argument("--output-file", default="",
                        help="Output file path (default: auto)")

    args = parser.parse_args()
    keywords = args.keyword

    # Filter by country
    sites = DEAL_SITES
    if args.countries:
        countries = [c.strip().lower() for c in args.countries.split(",")]
        sites = [s for s in DEAL_SITES if s["country"] in countries]

    scan_date = datetime.now().isoformat()
    print(f"\n{'═'*60}")
    print(f"  Deal Site RSS Fetcher")
    print(f"  Keywords: {', '.join(keywords)} | Sites: {len(sites)} | Workers: {args.workers}")
    if args.search_fallback:
        print(f"  Search fallback: ENABLED (Google)")
    if args.date_from and args.date_to:
        print(f"  Date range: {args.date_from} → {args.date_to}")
    print(f"{'═'*60}\n")

    all_posts = []
    failed_sites = []
    success_count = 0
    fallback_count = 0

    # Concurrent fetching
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_site = {
            executor.submit(
                fetch_site, site, keywords, args.timeout,
                args.search_fallback, args.date_from, args.date_to
            ): site
            for site in sites
        }

        for future in as_completed(future_to_site):
            site = future_to_site[future]
            try:
                site_info, posts, source, error = future.result()
                if posts:
                    all_posts.extend(posts)
                    if "fallback" in source or "search" in source:
                        fallback_count += 1
                        print(f"  [{site_info['country'].upper():2s}] {site_info['site']:25s} → {len(posts):3d} posts ({source})")
                    else:
                        success_count += 1
                        print(f"  [{site_info['country'].upper():2s}] {site_info['site']:25s} → {len(posts):3d} posts ({source})")
                else:
                    if error:
                        failed_sites.append({"site": site_info["site"], "country": site_info["country"],
                                              "error": error})
                        print(f"  [{site_info['country'].upper():2s}] {site_info['site']:25s} → FAILED ({error})")
            except Exception as e:
                failed_sites.append({"site": site["site"], "country": site["country"],
                                     "error": str(e)[:100]})
                print(f"  [{site['country'].upper():2s}] {site['site']:25s} → ERROR ({str(e)[:50]})")

    # Sort posts by country then date
    all_posts.sort(key=lambda p: (p["country"], p.get("pub_date", "")), reverse=True)

    # Output
    print(f"\n{'═'*60}")
    print(f"  RESULTS")
    print(f"{'═'*60}")
    print(f"  Sites scanned:   {len(sites)}")
    print(f"  Sites succeeded: {success_count} (RSS) + {fallback_count} (fallback)")
    print(f"  Sites failed:    {len(failed_sites)}")
    print(f"  Total posts:     {len(all_posts)}")

    if all_posts:
        # Group by country
        countries_found = set(p["country"] for p in all_posts)
        print(f"  Countries:       {', '.join(sorted(countries_found))}")
        needs_browser = sum(1 for p in all_posts if p.get("needs_browser"))
        print(f"  Needs browser:  {needs_browser} posts (Pepper sites)")

        print(f"\n{'─'*60}")
        for i, post in enumerate(all_posts, 1):
            print(f"\n  #{i}")
            print(f"  Site:      {post['site']} ({post['country'].upper()})")
            print(f"  Title:     {post['title'][:80]}")
            print(f"  Price:     {post.get('price', '—') or '—'}")
            print(f"  Date:      {post.get('pub_date', '—') or '—'}")
            print(f"  Comments:  {post.get('comments_count', '—') or '—'}")
            print(f"  Browser:   {'YES' if post.get('needs_browser') else 'no'}")
            print(f"  Source:    {post.get('source', 'rss')}")
            print(f"  Link:      {post['link'][:80]}")

    # Save output
    if args.output == "csv":
        output_str = output_csv(all_posts)
        ext = "csv"
    else:
        output_str = output_json(all_posts, failed_sites, keywords, scan_date)
        ext = "json"

    output_path = args.output_file or os.path.join(
        OUTPUT_DIR, f"deal_results_{keywords[0].replace(' ', '_')}.{ext}"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_str)

    print(f"\n  Results saved to: {output_path}")
    if failed_sites:
        print(f"  Failed sites ({len(failed_sites)}):")
        for fs in failed_sites[:10]:
            print(f"    - {fs['site']} ({fs['country'].upper()}): {fs['error']}")
        if len(failed_sites) > 10:
            print(f"    ... and {len(failed_sites) - 10} more")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
