#!/usr/bin/env python3
"""
Deal Site RSS Batch Fetcher

Scans 60+ deal sites across 11+ countries via RSS/Atom feeds.
Pure Python standard library — no required dependencies.

Usage:
  python rss_fetch.py -k "navimow"
  python rss_fetch.py -k anker -k soundcore -c us,de,uk --search-fallback
  python rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16
  python rss_fetch.py -k anker --output csv --workers 20
  python rss_fetch.py -k "robot lawn mower" --timeout 8
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
from datetime import datetime, timedelta, timezone

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
#  HTTP Fetching (urllib only — fast, no multi-backend fallback)
# ═══════════════════════════════════════════════════════════════════════

def fetch_url(url, timeout=8, extra_headers=None):
    """
    Fetch URL content using urllib only.
    Single attempt, no retry, no multi-backend fallback.
    Returns (content_str, backend_name) or (None, error_msg).
    """
    try:
        headers = {
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        if content and "just a moment" not in content.lower():
            return content, "urllib"
        return None, "cloudflare_blocked"
    except Exception as e:
        return None, str(e)[:60]


def fetch_google(url, timeout=10):
    """Fetch Google with consent cookie — improves reliability."""
    return fetch_url(url, timeout=timeout, extra_headers={
        "Cookie": "CONSENT=YES+cb.en+cd+px; SOCS=CAISHAgCEhJnd3NfMjAyNjA4MTUtMFNSdWADaBwA",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    })


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
            pub_date_parsed = ""
            if pub_date:
                dt = parse_date(pub_date.strip())
                if dt:
                    pub_date_parsed = dt.strftime('%Y-%m-%d %H:%M %Z')

            # Keyword filtering (OR match — any keyword hits)
            combined = (title + " " + summary).lower()
            if not any(kw.lower() in combined for kw in keywords):
                continue

            # Extract comments count (WordPress slash module)
            comments = ""
            comments_el = item.find("{http://purl.org/rss/1.0/modules/slash/}comments")
            if comments_el is not None and comments_el.text:
                comments = comments_el.text

            needs_browser = site_info.get("pepper", False)

            posts.append({
                "site": site_info["site"],
                "domain": site_info["domain"],
                "country": site_info["country"],
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.strip(),
                "pub_date_parsed": pub_date_parsed,
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
#  HTML Search Fallback (direct site search, no search engine needed)
# ═══════════════════════════════════════════════════════════════════════

def _strip_noise_tags(html):
    """Remove script, style, and noscript tags from HTML."""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    return html


def _is_valid_title(title):
    """Check if a title looks like real content, not JS code."""
    if not title or len(title) < 5:
        return False
    js_indicators = ['addEventListener', 'function(', 'var ', '&&', '||', '===',
                     'prototype', 'typeof', 'void(', '.af.', 'return ']
    if any(ind in title for ind in js_indicators):
        return False
    alpha_count = sum(1 for c in title if c.isalpha())
    if alpha_count < len(title) * 0.4:
        return False
    return True


def parse_date(date_str):
    """Parse various date formats and return timezone-aware datetime or None."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d %H:%M %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S",
                 "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
                 "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            continue
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except (ValueError, AttributeError):
        return None


def extract_date_from_html(html_context):
    """Extract publication date from HTML context. Returns (raw_date, parsed_date_str)."""
    now = datetime.now(timezone.utc)

    # 1. <time datetime="..."> or data attributes
    for attr in ['datetime', 'title', 'data-date', 'data-timestamp', 'data-time', 'content']:
        m = re.search(r'<time[^>]*' + attr + r'="([^"]+)"', html_context, re.I)
        if m:
            raw = m.group(1).strip()
            dt = parse_date(raw)
            if dt:
                return raw, dt.strftime('%Y-%m-%d %H:%M %Z')
            if raw.isdigit() and len(raw) >= 10:
                try:
                    ts = int(raw[:10])
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    return raw, dt.strftime('%Y-%m-%d %H:%M %Z')
                except (ValueError, OSError):
                    pass

    # 2. JSON-LD date patterns
    for p in [r'"datePublished"\s*:\s*"([^"]+)"', r'"dateCreated"\s*:\s*"([^"]+)"',
              r'data-published="([^"]+)"', r'data-submitted="([^"]+)"']:
        m = re.search(p, html_context, re.I)
        if m:
            raw = m.group(1).strip()
            dt = parse_date(raw)
            if dt:
                return raw, dt.strftime('%Y-%m-%d %H:%M %Z')

    # 3. Relative time — multi-language
    rel_patterns = [
        (r'(\d+)\s*(?:min|minute|m)\s*(?:ago|old)', 'minutes'),
        (r'(\d+)\s*(?:h|hour|hr)\s*(?:ago|old)', 'hours'),
        (r'(\d+)\s*(?:d|day)\s*(?:ago|old)', 'days'),
        (r'(\d+)\s*(?:w|week)\s*(?:ago|old)', 'weeks'),
        (r'just\s*now', 'just_now'),
        (r'yesterday', 'yesterday'),
        (r'vor\s+(\d+)\s*(?:min|stunde|std|tag|woche)', 'hours'),
        (r'gestern', 'yesterday'),
        (r'il y a\s+(\d+)\s*(?:min|h|heure|jour|semaine)', 'hours'),
        (r"hier", 'yesterday'),
        (r'hace\s+(\d+)\s*(?:min|h|hora|día|dia|semana)', 'hours'),
        (r'ayer', 'yesterday'),
        (r'temu\s+(\d+)\s*(?:min|h|godz|dzień|tydzień)', 'hours'),
        (r'(\d+)\s*(?:小时|天|周)前', 'hours'),
        (r'刚刚', 'just_now'),
        (r'昨天', 'yesterday'),
    ]
    for pattern, unit in rel_patterns:
        m = re.search(pattern, html_context, re.I)
        if m:
            raw = m.group(0).strip()
            if unit == 'just_now':
                dt = now
            elif unit == 'yesterday':
                dt = now - timedelta(days=1)
            else:
                try:
                    val = int(m.group(1))
                    delta = timedelta(**{unit: val})
                    dt = now - delta
                except (IndexError, ValueError):
                    continue
            return raw, dt.strftime('%Y-%m-%d %H:%M %Z')

    # 4. Absolute date in URL or context
    url_date = re.search(r'/(20\d{2})/(\d{1,2})/(\d{1,2})/', html_context)
    if url_date:
        raw = f"{url_date.group(1)}-{url_date.group(2)}-{url_date.group(3)}"
        dt = parse_date(raw)
        if dt:
            return raw, dt.strftime('%Y-%m-%d %H:%M %Z')

    abs_patterns = [r'(\w{3}\s+\d{1,2},?\s+\d{4})', r'(\d{1,2}[\./]\d{1,2}[\./]\d{4})',
                    r'(20\d{2}[\./-]\d{1,2}[\./-]\d{1,2})']
    for p in abs_patterns:
        m = re.search(p, html_context)
        if m:
            raw = m.group(1).strip()
            dt = parse_date(raw)
            if dt:
                return raw, dt.strftime('%Y-%m-%d %H:%M %Z')

    return "", ""


def search_site_direct(site_info, keywords, timeout=10):
    """Fetch the site's own search page directly — no Google/Bing needed.
    Extracts deal links from the site's HTML search results."""
    if not site_info.get("search_url"):
        return []

    search_url = site_info["search_url"].format(
        q=urllib.parse.quote(keywords[0]) if keywords else ""
    )
    content, backend = fetch_url(search_url, timeout=timeout)
    if not content:
        return []

    content = _strip_noise_tags(content)
    domain = site_info["domain"]
    escaped = re.escape(domain)

    # Find all anchor tags with hrefs pointing to the site's domain
    anchor_pattern = re.compile(
        rf'<a[^>]*href="((?:https?://(?:www\.)?{escaped})?(/[^\s"\'<>]+))"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE
    )

    results = []
    seen = set()
    for m in anchor_pattern.finditer(content):
        href = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        text = text[:200]

        if not _is_valid_title(text):
            continue
        if any(kw.lower() in text.lower() for kw in keywords):
            # Build full URL
            if href.startswith("http"):
                full_url = href
            else:
                full_url = f"https://{domain}{href}" if href.startswith("/") else f"https://{domain}/{href}"

            if full_url not in seen and '/search' not in full_url.lower():
                seen.add(full_url)
                # Extract date from surrounding HTML context
                ctx_start = max(0, m.start() - 800)
                ctx_end = min(len(content), m.end() + 800)
                context = content[ctx_start:ctx_end]
                pub_date, pub_date_parsed = extract_date_from_html(context)
                results.append((text, full_url, pub_date, pub_date_parsed))

    return results[:15]


def search_fallback_parallel(site_domain, keywords, timeout=10, site_info=None):
    """Direct site search fallback — fetches site's own search page.
    No external search engines needed."""
    if site_info:
        return search_site_direct(site_info, keywords, timeout=timeout)
    return []


# ═══════════════════════════════════════════════════════════════════════
#  Site Fetcher (single site — optimized)
# ═══════════════════════════════════════════════════════════════════════

def fetch_site(site_info, keywords, timeout, search_fallback, date_from, date_to):
    """
    Fetch deals from a single site.
    Strategy:
      1. RSS (8s, urllib only, no retry)
      2. If RSS fails AND search_fallback enabled:
         - Pepper sites: skip (use ScraperAPI)
         - Non-Pepper: Google + Google News in PARALLEL (~10s)
    """
    rss_url = site_info["rss_url"].format(
        q=urllib.parse.quote(keywords[0]) if keywords else ""
    )

    # 1. Try RSS (single attempt, urllib only)
    content, backend = fetch_url(rss_url, timeout=timeout)

    if content:
        posts = parse_rss(content, site_info, keywords)
        if posts:
            for p in posts:
                p["source"] = "rss"
            return site_info, posts, f"rss ({backend})", None

    # 2. RSS failed — skip Pepper sites (they need ScraperAPI)
    if site_info.get("pepper", False):
        return site_info, [], "skipped_pepper", "Cloudflare (use ScraperAPI)"

    # 3. Non-Pepper: direct site search fallback (if enabled)
    if search_fallback:
        results = search_fallback_parallel(
            site_info["domain"], keywords, timeout=10, site_info=site_info
        )
        if results:
            posts = []
            for title, url, pub_date, pub_date_parsed in results:
                combined = (title + " " + url).lower()
                if any(kw.lower() in combined for kw in keywords):
                    posts.append({
                        "site": site_info["site"],
                        "domain": site_info["domain"],
                        "country": site_info["country"],
                        "title": title,
                        "link": url,
                        "pub_date": pub_date,
                        "pub_date_parsed": pub_date_parsed,
                        "summary": "",
                        "price": extract_price(title),
                        "temperature": "",
                        "votes": "",
                        "comments_count": "",
                        "needs_browser": site_info.get("pepper", False),
                        "source": "site_search",
                    })
            if posts:
                return site_info, posts, "site_search", None

    error = "RSS failed" if not content else "No keyword matches"
    return site_info, [], "none", error


# ═══════════════════════════════════════════════════════════════════════
#  Output Formatting
# ═══════════════════════════════════════════════════════════════════════

def output_json(all_posts, failed_sites, keywords, scan_date, elapsed):
    """Generate JSON output."""
    return json.dumps({
        "keyword": " + ".join(keywords),
        "scan_date": scan_date,
        "elapsed_seconds": round(elapsed, 1),
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
    parser.add_argument("--timeout", type=int, default=8,
                        help="Per-site request timeout in seconds (default: 8)")
    parser.add_argument("--output", default="json", choices=["json", "csv"],
                        help="Output format (default: json)")
    parser.add_argument("--search-fallback", action="store_true",
                        help="Use Google search fallback for RSS-failed sites")
    parser.add_argument("--workers", type=int, default=20,
                        help="Concurrent workers (default: 20)")
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
    print(f"  Timeout: {args.timeout}s per site | Backend: urllib only")
    if args.search_fallback:
        print(f"  Search fallback: ENABLED (direct site search)")
    if args.date_from and args.date_to:
        print(f"  Date range: {args.date_from} → {args.date_to}")
    print(f"{'═'*60}\n")

    all_posts = []
    failed_sites = []
    success_count = 0
    fallback_count = 0
    start_time = time.time()

    # Concurrent fetching — all sites in parallel
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
            elapsed = time.time() - start_time
            try:
                site_info, posts, source, error = future.result()
                if posts:
                    all_posts.extend(posts)
                    if "fallback" in source or "search" in source:
                        fallback_count += 1
                    else:
                        success_count += 1
                    print(f"  [{elapsed:5.1f}s] [{site_info['country'].upper():2s}] {site_info['site']:25s} → {len(posts):3d} posts ({source})")
                else:
                    if error:
                        failed_sites.append({"site": site_info["site"], "country": site_info["country"],
                                              "error": error})
                        print(f"  [{elapsed:5.1f}s] [{site_info['country'].upper():2s}] {site_info['site']:25s} → FAIL ({error})")
            except Exception as e:
                failed_sites.append({"site": site["site"], "country": site["country"],
                                     "error": str(e)[:100]})
                print(f"  [{elapsed:5.1f}s] [{site['country'].upper():2s}] {site['site']:25s} → ERROR ({str(e)[:50]})")

    elapsed_total = time.time() - start_time

    # Sort posts by country then date
    all_posts.sort(key=lambda p: (p["country"], p.get("pub_date", "")), reverse=True)

    # Output
    print(f"\n{'═'*60}")
    print(f"  RESULTS — {elapsed_total:.1f}s total")
    print(f"{'═'*60}")
    print(f"  Sites scanned:   {len(sites)}")
    print(f"  Sites succeeded: {success_count} (RSS) + {fallback_count} (fallback)")
    print(f"  Sites failed:    {len(failed_sites)}")
    print(f"  Total posts:     {len(all_posts)}")

    if all_posts:
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
            print(f"  Source:    {post.get('source', 'rss')}")

    # Save output
    if args.output == "csv":
        output_str = output_csv(all_posts)
        ext = "csv"
    else:
        output_str = output_json(all_posts, failed_sites, keywords, scan_date, elapsed_total)
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
