#!/usr/bin/env python3
"""
Deal 站品牌关键词监测脚本（v2 - 优化抓取成功率）

通过 RSS 批量抓取全球 60+ deal 站的最新帖子，按品牌关键词过滤。
优化：403 站点自动走 rss2json 代理，失败后自动从首页发现 RSS。

用法:
    python rss_fetch.py -k "anker" -c us,de,uk
    python rss_fetch.py -k mammotion -k navimow
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote_plus, urljoin

# ============================================================
# 站点配置
# proxy=True 的站点有 Cloudflare 反爬，直连 403，走 rss2json 代理
# pepper=True 的站点支持 /rss/search?q=keyword 搜索 RSS
# ============================================================
SITES = [
    # 美国
    {"domain": "dealnews.com", "country": "us", "name": "DealNews", "rss_url": "https://www.dealnews.com/?rss=1", "pepper": False, "proxy": False},
    {"domain": "slickdeals.net", "country": "us", "name": "Slickdeals", "rss_url": "https://slickdeals.net/rss/", "pepper": True, "proxy": True},
    {"domain": "dealseek.com", "country": "us", "name": "DealSeek", "rss_url": "https://www.dealseek.com/feed/", "pepper": False, "proxy": False},
    {"domain": "techbargains.com", "country": "us", "name": "TechBargains", "rss_url": "https://www.techbargains.com/rss.xml", "pepper": False, "proxy": False},
    {"domain": "myvipon.com", "country": "us", "name": "MyVipon", "rss_url": "https://www.myvipon.com/feed/", "pepper": False, "proxy": True},
    {"domain": "koupon.ai", "country": "us", "name": "Koupon.ai", "rss_url": "https://koupon.ai/feed/", "pepper": False, "proxy": False},
    {"domain": "dealsofamerica.com", "country": "us", "name": "Deals of America", "rss_url": "https://www.dealsofamerica.com/arss.xml", "pepper": False, "proxy": False},
    {"domain": "bensbargains.com", "country": "us", "name": "BensBargains", "rss_url": "https://bensbargains.com/feed/", "pepper": False, "proxy": True},
    {"domain": "freestufffinder.com", "country": "us", "name": "Free Stuff Finder", "rss_url": "https://freestufffinder.com/feed/", "pepper": False, "proxy": False},
    {"domain": "edealinfo.com", "country": "us", "name": "eDealInfo", "rss_url": "https://www.edealinfo.com/rss.xml", "pepper": False, "proxy": True},
    {"domain": "1sale.com", "country": "us", "name": "1Sale", "rss_url": "https://1sale.com/feed/", "pepper": False, "proxy": False},
    {"domain": "dealwiki.com", "country": "us", "name": "DealWiki", "rss_url": "https://dealwiki.com/feed/", "pepper": False, "proxy": True},
    {"domain": "21usdeal.com", "country": "us", "name": "21usDeal", "rss_url": "https://21usdeal.com/en/feed/", "pepper": False, "proxy": False},
    {"domain": "ihotoffers.com", "country": "us", "name": "iHotOffers", "rss_url": "https://www.ihotoffers.com/feed/", "pepper": False, "proxy": True},
    {"domain": "swaggrabber.com", "country": "us", "name": "SwagGrabber", "rss_url": "https://swaggrabber.com/feed/", "pepper": False, "proxy": False},
    {"domain": "shopsale.com", "country": "us", "name": "ShopSale", "rss_url": "https://www.shopsale.com/rss.php", "pepper": False, "proxy": True},
    {"domain": "fabulesslyfrugal.com", "country": "us", "name": "Fabulessly Frugal", "rss_url": "https://fabulesslyfrugal.com/feed/", "pepper": False, "proxy": False},
    {"domain": "dansdeals.com", "country": "us", "name": "DansDeals", "rss_url": "https://www.dansdeals.com/feed/", "pepper": False, "proxy": False},
    {"domain": "reddit.com", "country": "us", "name": "Reddit r/deals", "rss_url": "https://www.reddit.com/r/deals/.rss", "pepper": False, "proxy": False},
    {"domain": "struggleville.net", "country": "us", "name": "Struggleville", "rss_url": "https://www.struggleville.net/feed/", "pepper": False, "proxy": False},
    {"domain": "dealam.com", "country": "us", "name": "DealAM", "rss_url": "https://www.dealam.com/rss.xml", "pepper": False, "proxy": False},
    {"domain": "simplexdeals.com", "country": "us", "name": "SimplexDeals", "rss_url": "https://simplexdeals.com/feed/", "pepper": False, "proxy": True},
    {"domain": "moneysavingmom.com", "country": "us", "name": "Money Saving Mom", "rss_url": "https://www.moneysavingmom.com/feed/", "pepper": False, "proxy": False},
    {"domain": "hip2save.com", "country": "us", "name": "Hip2Save", "rss_url": "https://hip2save.com/feed/", "pepper": False, "proxy": False},
    # 加拿大
    {"domain": "savealoonie.com", "country": "ca", "name": "SaveaLoonie", "rss_url": "https://www.savealoonie.com/feed/", "pepper": False, "proxy": False},
    {"domain": "redflagdeals.com", "country": "ca", "name": "RedFlagDeals", "rss_url": "https://forums.redflagdeals.com/rss/", "pepper": True, "proxy": True},
    # 德国
    {"domain": "dealgott.de", "country": "de", "name": "Dealgott", "rss_url": "https://www.dealgott.de/feed/", "pepper": False, "proxy": False},
    {"domain": "mein-deal.com", "country": "de", "name": "Mein-Deal", "rss_url": "https://www.mein-deal.com/feed/", "pepper": False, "proxy": False},
    {"domain": "dealbunny.de", "country": "de", "name": "DealBunny", "rss_url": "https://www.dealbunny.de/feed/", "pepper": False, "proxy": False},
    {"domain": "snipz.de", "country": "de", "name": "Snipz", "rss_url": "https://snipz.de/feed/", "pepper": False, "proxy": False},
    {"domain": "monsterdealz.de", "country": "de", "name": "MonsterDealz", "rss_url": "https://www.monsterdealz.de/feed/", "pepper": False, "proxy": False},
    {"domain": "dealdoktor.de", "country": "de", "name": "DealDoktor", "rss_url": "https://www.dealdoktor.de/feed/", "pepper": False, "proxy": False},
    {"domain": "mydealz.de", "country": "de", "name": "MyDealz", "rss_url": "https://www.mydealz.de/rss/", "pepper": True, "proxy": True},
    {"domain": "mytopdeals.net", "country": "de", "name": "MyTopDeals", "rss_url": "https://www.mytopdeals.net/feed/", "pepper": False, "proxy": False},
    {"domain": "sparbote.de", "country": "de", "name": "Sparbote", "rss_url": "https://www.sparbote.de/feed/", "pepper": False, "proxy": False},
    {"domain": "dealonkel.de", "country": "de", "name": "Dealonkel", "rss_url": "https://www.dealonkel.de/rss.xml", "pepper": False, "proxy": False},
    # 英国
    {"domain": "hotukdeals.com", "country": "uk", "name": "HotUKDeals", "rss_url": "https://www.hotukdeals.com/rss/", "pepper": True, "proxy": True},
    {"domain": "latestdeals.co.uk", "country": "uk", "name": "LatestDeals", "rss_url": "https://www.latestdeals.co.uk/feeds/rss", "pepper": False, "proxy": False},
    # 法国
    {"domain": "dealabs.com", "country": "fr", "name": "Dealabs", "rss_url": "https://www.dealabs.com/rss/", "pepper": True, "proxy": True},
    {"domain": "serialdealer.fr", "country": "fr", "name": "SerialDealer", "rss_url": "https://www.serialdealer.fr/feed/", "pepper": False, "proxy": False},
    {"domain": "bons-plans-malins.com", "country": "fr", "name": "Bons Plans Malins", "rss_url": "https://www.bons-plans-malins.com/feed/", "pepper": False, "proxy": False},
    # 意大利
    {"domain": "scontify.net", "country": "it", "name": "Scontify", "rss_url": "https://www.scontify.net/feed/", "pepper": False, "proxy": False},
    {"domain": "bestdiscount.it", "country": "it", "name": "BestDiscount", "rss_url": "https://www.bestdiscount.it/feed/", "pepper": False, "proxy": False},
    {"domain": "wikideal.it", "country": "it", "name": "WikiDeal", "rss_url": "https://www.wikideal.it/feed/", "pepper": False, "proxy": False},
    {"domain": "tuttotek.it", "country": "it", "name": "TuttoTek", "rss_url": "https://www.tuttotek.it/feed/", "pepper": False, "proxy": False},
    # 西班牙
    {"domain": "chollometro.com", "country": "es", "name": "Chollometro", "rss_url": "https://www.chollometro.com/rss/", "pepper": True, "proxy": True},
    {"domain": "super-chollos.com", "country": "es", "name": "SuperChollos", "rss_url": "https://www.super-chollos.com/feed/", "pepper": False, "proxy": False},
    {"domain": "cholloterapia.com", "country": "es", "name": "Cholloterapia", "rss_url": "https://www.cholloterapia.com/feed/", "pepper": False, "proxy": False},
    {"domain": "soydechollos.com", "country": "es", "name": "SoyDeChollos", "rss_url": "https://www.soydechollos.com/feed/", "pepper": False, "proxy": False},
    {"domain": "michollo.com", "country": "es", "name": "MiChollo", "rss_url": "https://www.michollo.com/feed/", "pepper": False, "proxy": False},
    {"domain": "cholloschina.com", "country": "es", "name": "ChollosChina", "rss_url": "https://www.cholloschina.com/feed/", "pepper": False, "proxy": False},
    {"domain": "mepicaelchollo.com", "country": "es", "name": "MePicaElChollo", "rss_url": "https://www.mepicaelchollo.com/feed/", "pepper": False, "proxy": False},
    {"domain": "nolodejesescapar.com", "country": "es", "name": "NoLoDejesEscapar", "rss_url": "https://www.nolodejesescapar.com/feed/", "pepper": False, "proxy": False},
    # 墨西哥
    {"domain": "promodescuentos.com", "country": "mx", "name": "Promodescuentos", "rss_url": "https://www.promodescuentos.com/rss/", "pepper": True, "proxy": True},
    {"domain": "megadescuentos.com", "country": "mx", "name": "Megadescuentos", "rss_url": "https://www.megadescuentos.com/feed/", "pepper": False, "proxy": False},
    # 波兰
    {"domain": "pepper.pl", "country": "pl", "name": "Pepper.pl", "rss_url": "https://www.pepper.pl/rss/", "pepper": True, "proxy": True},
    {"domain": "hotshops.pl", "country": "pl", "name": "HotShops", "rss_url": "https://www.hotshops.pl/feed/", "pepper": False, "proxy": False},
    # 巴西
    {"domain": "gatry.com", "country": "br", "name": "Gatry", "rss_url": "https://www.gatry.com/feed/", "pepper": False, "proxy": False},
    {"domain": "promobit.com.br", "country": "br", "name": "Promobit", "rss_url": "https://www.promobit.com.br/rss/", "pepper": True, "proxy": True},
    {"domain": "pelando.com.br", "country": "br", "name": "Pelando", "rss_url": "https://www.pelando.com.br/rss/", "pepper": True, "proxy": True},
    # 澳大利亚
    {"domain": "ozbargain.com.au", "country": "au", "name": "OzBargain", "rss_url": "https://www.ozbargain.com.au/rss.xml", "pepper": False, "proxy": False},
]

RSS_FALLBACK_PATHS = ["/feed/", "/rss/", "/rss.xml", "/feed.xml", "/?feed=rss2"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_url(url, timeout=12):
    """直接抓取 URL，返回 bytes 或 None"""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception:
        pass
    return None


def fetch_via_proxy(rss_url, timeout=15):
    """通过 rss2json.com 代理抓取 RSS（绕过 Cloudflare 403），返回 bytes 或 None"""
    proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={quote_plus(rss_url)}"
    req = urllib.request.Request(proxy_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = resp.read()
                # 验证是有效 JSON 且 status=ok
                try:
                    obj = json.loads(data)
                    if obj.get("status") == "ok" and obj.get("items"):
                        return data
                except Exception:
                    pass
    except Exception:
        pass
    return None


def discover_rss_from_homepage(domain, timeout=10):
    """访问站点首页，自动发现 RSS 链接，返回 RSS URL 或 None"""
    homepage = f"https://www.{domain}/"
    req = urllib.request.Request(homepage, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            html = resp.read().decode("utf-8", errors="ignore")
            # 查找 link rel=alternate type=rss
            m = re.search(r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
            if m:
                rss_url = m.group(1)
                if rss_url.startswith("//"):
                    rss_url = "https:" + rss_url
                elif rss_url.startswith("/"):
                    rss_url = urljoin(homepage, rss_url)
                return rss_url
            # 退而求其次：找包含 feed/rss 的 href
            matches = re.findall(r'href=["\']([^"\']*(?:feed|rss)[^"\']*)["\']', html, re.I)
            for m in matches:
                if not m.endswith((".css", ".js")) and "comment" not in m.lower():
                    if m.startswith("//"):
                        m = "https:" + m
                    elif m.startswith("/"):
                        m = urljoin(homepage, m)
                    return m
    except Exception:
        pass
    return None


def get_rss_content(site, keywords, timeout=12):
    """
    获取站点 RSS 内容，按优先级：
    1. Pepper 站搜索 RSS（走代理）
    2. 配置的 RSS URL（proxy 站走代理，否则直连）
    3. 常见路径回退
    4. 首页自动发现
    返回 (content_bytes, used_url, source) 或 (None, None, None)
    """
    # 1. Pepper 搜索 RSS
    if site["pepper"] and keywords:
        search_url = f"https://www.{site['domain']}/rss/search?q={quote_plus(keywords[0])}"
        if site["proxy"]:
            content = fetch_via_proxy(search_url, timeout)
            if content:
                return content, search_url, "proxy_search"
        else:
            content = fetch_url(search_url, timeout)
            if content:
                return content, search_url, "direct_search"

    # 2. 配置的 RSS URL
    rss_url = site["rss_url"]
    if site["proxy"]:
        content = fetch_via_proxy(rss_url, timeout)
        if content:
            return content, rss_url, "proxy_main"
    else:
        content = fetch_url(rss_url, timeout)
        if content:
            return content, rss_url, "direct_main"

    # 3. 常见路径回退（仅非 proxy 站）
    if not site["proxy"]:
        for path in RSS_FALLBACK_PATHS:
            fallback_url = f"https://www.{site['domain']}{path}"
            content = fetch_url(fallback_url, timeout)
            if content:
                return content, fallback_url, "direct_fallback"

    # 4. 首页自动发现（仅非 proxy 站）
    if not site["proxy"]:
        discovered = discover_rss_from_homepage(site["domain"], timeout)
        if discovered:
            content = fetch_url(discovered, timeout)
            if content:
                return content, discovered, "direct_discovered"

    return None, None, None


def parse_rss_xml(xml_bytes, site, keyword_lower_list):
    """解析 RSS/Atom XML，返回匹配帖子列表"""
    results = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return results

    items = root.findall(".//item")
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", ns)

    for item in items:
        title_el = item.find("title")
        title = unescape(title_el.text.strip()) if title_el is not None and title_el.text else ""

        link = ""
        link_el = item.find("link")
        if link_el is not None:
            if link_el.text:
                link = link_el.text.strip()
            elif link_el.get("href"):
                link = link_el.get("href").strip()

        pub_date = ""
        for tag in ["pubDate", "published", "updated", "date"]:
            el = item.find(tag)
            if el is not None and el.text:
                pub_date = el.text.strip()
                break

        summary = ""
        for tag in ["description", "summary", "content"]:
            el = item.find(tag)
            if el is not None and el.text:
                summary = unescape(re.sub(r"<[^>]+>", "", el.text)).strip()
                break
        if not summary:
            for child in item:
                if child.tag.endswith("encoded") and child.text:
                    summary = unescape(re.sub(r"<[^>]+>", "", child.text)).strip()
                    break

        # 评论链接和评论数（WordPress 有 <comments>链接 和 <slash:comments>数字）
        comments_link = ""
        comments_count = ""
        for child in item:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "comments" and child.text:
                if child.text.strip().isdigit():
                    comments_count = child.text.strip()
                else:
                    comments_link = child.text.strip()
            elif tag == "commentRss" and child.text:
                comments_link = child.text.strip()

        # 温度/投票（Pepper RSS 可能不含，标注需浏览器补全）
        temperature = ""
        votes = ""
        for child in item:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if "temperature" in tag.lower() or "hot" in tag.lower():
                temperature = child.text.strip() if child.text else ""
            elif "vote" in tag.lower() or "score" in tag.lower():
                votes = child.text.strip() if child.text else ""

        needs_browser = site.get("pepper", False) or site.get("proxy", False)

        text_blob = (title + " " + summary).lower()
        matched = [kw for kw in keyword_lower_list if kw in text_blob]
        if matched:
            results.append({
                "site": site["name"], "domain": site["domain"],
                "country": site["country"].upper(), "title": title,
                "link": link, "pub_date": pub_date,
                "summary": summary[:500],
                "comments_count": comments_count,
                "comments_link": comments_link,
                "temperature": temperature,
                "votes": votes,
                "needs_browser": needs_browser,
                "matched_keywords": matched,
            })
    return results


def parse_rss_json(json_bytes, site, keyword_lower_list):
    """解析 rss2json 代理返回的 JSON 格式"""
    results = []
    try:
        obj = json.loads(json_bytes)
    except Exception:
        return results

    for item in obj.get("items", []):
        title = item.get("title", "")
        link = item.get("link", "")
        pub_date = item.get("pubDate", "")
        summary = unescape(re.sub(r"<[^>]+>", "", item.get("description", "") or item.get("content", ""))).strip()
        comments = str(item.get("comments", ""))

        text_blob = (title + " " + summary).lower()
        matched = [kw for kw in keyword_lower_list if kw in text_blob]
        if matched:
            results.append({
                "site": site["name"], "domain": site["domain"],
                "country": site["country"].upper(), "title": title,
                "link": link, "pub_date": pub_date,
                "summary": summary[:500],
                "comments_count": str(item.get("comments", "")),
                "comments_link": "",
                "temperature": "",
                "votes": "",
                "needs_browser": site.get("pepper", False) or site.get("proxy", False),
                "matched_keywords": matched,
            })
    return results


def search_google_news(site, keywords, timeout=15):
    """Google News RSS 搜索回退：对无 RSS 或反爬严格的站点，用 site: 搜索获取帖子"""
    query = quote_plus(f"site:{site['domain']} {' '.join(keywords)}")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return []
            data = resp.read()
    except Exception:
        return []

    results = []
    try:
        root = ET.fromstring(data)
        items = root.findall(".//item")
    except ET.ParseError:
        return []

    for item in items[:20]:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        summary = unescape(re.sub(r"<[^>]+>", "", item.findtext("description", ""))).strip()

        text_blob = (title + " " + summary).lower()
        matched = [kw for kw in keywords if kw in text_blob]
        if matched:
            results.append({
                "site": site["name"], "domain": site["domain"],
                "country": site["country"].upper(), "title": title,
                "link": link, "pub_date": pub_date,
                "summary": summary[:500],
                "comments_count": "",
                "comments_link": "",
                "temperature": "",
                "votes": "",
                "needs_browser": True,
                "matched_keywords": matched,
                "source": "google_news_fallback",
            })
    return results


def main():
    parser = argparse.ArgumentParser(description="Deal 站品牌关键词 RSS 监测 v2")
    parser.add_argument("--keyword", "-k", action="append", required=True)
    parser.add_argument("--countries", "-c", default=None)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--output", choices=["json", "csv"], default="json")
    parser.add_argument("--search-fallback", action="store_true",
                        help="RSS 失败的站点用 Google News 搜索回退（覆盖更全但结果可能不精准）")
    args = parser.parse_args()

    keywords = [kw.strip().lower() for kw in args.keyword if kw.strip()]
    if not keywords:
        print("错误：至少需要一个关键词", file=sys.stderr)
        sys.exit(1)

    countries = None
    if args.countries:
        countries = set(c.strip().lower() for c in args.countries.split(",") if c.strip())

    sites_to_check = SITES
    if countries:
        sites_to_check = [s for s in SITES if s["country"] in countries]

    all_matches = []
    failed_sites = []
    stats = {"total": len(sites_to_check), "success": 0, "failed": 0, "matches": 0,
             "by_source": {"direct": 0, "proxy": 0, "fallback": 0, "discovered": 0, "google_news": 0}}

    for site in sites_to_check:
        content, used_url, source = get_rss_content(site, keywords, args.timeout)
        if content is None:
            # Google News 搜索回退
            if args.search_fallback:
                gn_matches = search_google_news(site, keywords, args.timeout)
                if gn_matches:
                    all_matches.extend(gn_matches[:args.max_items])
                    stats["matches"] += len(gn_matches[:args.max_items])
                    stats["by_source"]["google_news"] += 1
                    continue
            stats["failed"] += 1
            failed_sites.append(site["domain"])
            continue

        stats["success"] += 1
        if source.startswith("proxy"):
            stats["by_source"]["proxy"] += 1
        elif source.startswith("direct"):
            stats["by_source"]["direct"] += 1
        elif "fallback" in source:
            stats["by_source"]["fallback"] += 1
        elif "discovered" in source:
            stats["by_source"]["discovered"] += 1

        # rss2json 返回 JSON，其他返回 XML
        if source.startswith("proxy"):
            matches = parse_rss_json(content, site, keywords)
        else:
            matches = parse_rss_xml(content, site, keywords)

        if matches:
            matches = matches[:args.max_items]
            all_matches.extend(matches)
            stats["matches"] += len(matches)

    # 按时间倒序
    def sort_key(item):
        date_str = item.get("pub_date", "")
        try:
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S GMT"]:
                try:
                    return datetime.strptime(date_str, fmt).timestamp()
                except ValueError:
                    continue
        except Exception:
            pass
        return 0

    all_matches.sort(key=sort_key, reverse=True)

    # 去重
    seen = set()
    unique = []
    for m in all_matches:
        link = m.get("link", "")
        if link and link not in seen:
            seen.add(link)
            unique.append(m)
        elif not link:
            unique.append(m)

    output = {
        "query": {"keywords": args.keyword, "countries": args.countries or "all",
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  "search_fallback": args.search_fallback},
        "stats": stats,
        "failed_sites": failed_sites,
        "total_matches": len(unique),
        "posts": unique,
    }

    if args.output == "csv":
        import csv
        w = csv.writer(sys.stdout)
        w.writerow(["country", "site", "domain", "title", "link", "pub_date", "comments_count", "temperature", "votes", "needs_browser", "matched_keywords", "summary"])
        for p in unique:
            w.writerow([p["country"], p["site"], p["domain"], p["title"], p["link"],
                        p["pub_date"], p.get("comments_count",""), p.get("temperature",""),
                        p.get("votes",""), p.get("needs_browser",False),
                        "|".join(p["matched_keywords"]), p["summary"][:200]])
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
