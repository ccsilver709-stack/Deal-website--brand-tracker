#!/usr/bin/env python3
"""
Deal 站品牌关键词监测脚本 v4

核心改进：
- 并发抓取（ThreadPoolExecutor，10 线程），61 站从 12 分钟降到 1-2 分钟
- Pepper 站优先用搜索 RSS（/rss/search?q=keyword），命中率远高于全站过滤
- Cloudflare 站直接走 rss2json 代理，不先试直连（节省时间）
- 自动提取 slash:comments 评论数
- 输出 needs_browser 标记，指导 AI 助手补全温度/投票

用法:
    python rss_fetch.py -k anker
    python rss_fetch.py -k mammotion -k navimow -c de,uk,fr
    python rss_fetch.py -k anker --search-fallback
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from urllib.parse import quote_plus

# ============================================================
# 站点配置
# pepper=True: 支持 /rss/search?q=keyword 搜索 RSS
# proxy=True: 有 Cloudflare，直连 403，直接走 rss2json 代理
# ============================================================
SITES = [
    # 美国 (24)
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
    # 加拿大 (2)
    {"domain": "savealoonie.com", "country": "ca", "name": "SaveaLoonie", "rss_url": "https://www.savealoonie.com/feed/", "pepper": False, "proxy": False},
    {"domain": "redflagdeals.com", "country": "ca", "name": "RedFlagDeals", "rss_url": "https://forums.redflagdeals.com/rss/", "pepper": True, "proxy": True},
    # 德国 (10)
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
    # 英国 (2)
    {"domain": "hotukdeals.com", "country": "uk", "name": "HotUKDeals", "rss_url": "https://www.hotukdeals.com/rss/", "pepper": True, "proxy": True},
    {"domain": "latestdeals.co.uk", "country": "uk", "name": "LatestDeals", "rss_url": "https://www.latestdeals.co.uk/feeds/rss", "pepper": False, "proxy": False},
    # 法国 (3)
    {"domain": "dealabs.com", "country": "fr", "name": "Dealabs", "rss_url": "https://www.dealabs.com/rss/", "pepper": True, "proxy": True},
    {"domain": "serialdealer.fr", "country": "fr", "name": "SerialDealer", "rss_url": "https://www.serialdealer.fr/feed/", "pepper": False, "proxy": False},
    {"domain": "bons-plans-malins.com", "country": "fr", "name": "Bons Plans Malins", "rss_url": "https://www.bons-plans-malins.com/feed/", "pepper": False, "proxy": False},
    # 意大利 (5)
    {"domain": "scontify.net", "country": "it", "name": "Scontify", "rss_url": "https://www.scontify.net/feed/", "pepper": False, "proxy": True},
    {"domain": "bestdiscount.it", "country": "it", "name": "BestDiscount", "rss_url": "https://www.bestdiscount.it/feed/", "pepper": False, "proxy": False},
    {"domain": "wikideal.it", "country": "it", "name": "WikiDeal", "rss_url": "https://www.wikideal.it/feed/", "pepper": False, "proxy": False},
    {"domain": "hotshops.it", "country": "it", "name": "HotShops IT", "rss_url": "https://www.hotshops.it/feed/", "pepper": False, "proxy": False},
    {"domain": "tuttotek.it", "country": "it", "name": "TuttoTek", "rss_url": "https://www.tuttotek.it/feed/", "pepper": False, "proxy": False},
    # 西班牙 (8)
    {"domain": "chollometro.com", "country": "es", "name": "Chollometro", "rss_url": "https://www.chollometro.com/rss/", "pepper": True, "proxy": True},
    {"domain": "super-chollos.com", "country": "es", "name": "SuperChollos", "rss_url": "https://www.super-chollos.com/feed/", "pepper": False, "proxy": False},
    {"domain": "cholloterapia.com", "country": "es", "name": "Cholloterapia", "rss_url": "https://www.cholloterapia.com/feed/", "pepper": False, "proxy": False},
    {"domain": "soydechollos.com", "country": "es", "name": "SoydeChollos", "rss_url": "https://www.soydechollos.com/feed/", "pepper": False, "proxy": False},
    {"domain": "michollo.com", "country": "es", "name": "MiChollo", "rss_url": "https://www.michollo.com/feed/", "pepper": False, "proxy": False},
    {"domain": "cholloschina.com", "country": "es", "name": "ChollosChina", "rss_url": "https://www.cholloschina.com/feed/", "pepper": False, "proxy": False},
    {"domain": "mepicaelchollo.com", "country": "es", "name": "MePicaElChollo", "rss_url": "https://www.mepicaelchollo.com/feed/", "pepper": False, "proxy": False},
    {"domain": "nolodejesescapar.com", "country": "es", "name": "NoLoDejesEscapar", "rss_url": "https://www.nolodejesescapar.com/feed/", "pepper": False, "proxy": False},
    # 墨西哥 (2)
    {"domain": "promodescuentos.com", "country": "mx", "name": "Promodescuentos", "rss_url": "https://www.promodescuentos.com/rss/", "pepper": True, "proxy": True},
    {"domain": "megadescuentos.com", "country": "mx", "name": "Megadescuentos", "rss_url": "https://www.megadescuentos.com/feed/", "pepper": False, "proxy": False},
    # 波兰 (2)
    {"domain": "pepper.pl", "country": "pl", "name": "Pepper.pl", "rss_url": "https://www.pepper.pl/rss/", "pepper": True, "proxy": True},
    {"domain": "hotshops.pl", "country": "pl", "name": "HotShops PL", "rss_url": "https://www.hotshops.pl/feed/", "pepper": False, "proxy": True},
    # 巴西 (3)
    {"domain": "gatry.com", "country": "br", "name": "Gatry", "rss_url": "https://www.gatry.com/feed/", "pepper": False, "proxy": False},
    {"domain": "promobit.com.br", "country": "br", "name": "Promobit", "rss_url": "https://www.promobit.com.br/rss/", "pepper": True, "proxy": True},
    {"domain": "pelando.com.br", "country": "br", "name": "Pelando", "rss_url": "https://www.pelando.com.br/rss/", "pepper": True, "proxy": True},
    # 澳大利亚 (1)
    {"domain": "ozbargain.com.au", "country": "au", "name": "OzBargain", "rss_url": "https://www.ozbargain.com.au/rss.xml", "pepper": False, "proxy": False},
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# 常见 RSS 路径回退
RSS_FALLBACK_PATHS = ["/feed/", "/rss/", "/rss.xml", "/feed.xml", "/?feed=rss2", "/feeds/posts/default"]


def fetch_url(url, timeout=10):
    """请求 URL，返回 bytes 或 None"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def fetch_via_proxy(rss_url, timeout=15):
    """通过 rss2json 代理抓取，返回 JSON dict 或 None"""
    proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={quote_plus(rss_url)}"
    try:
        req = urllib.request.Request(proxy_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "ok" and data.get("items"):
                return data
    except Exception:
        pass
    return None


def get_pepper_search_url(site, keyword):
    """生成 Pepper 站搜索 RSS URL"""
    domain = site["domain"]
    if domain == "redflagdeals.com":
        return f"https://forums.redflagdeals.com/rss/?q={quote_plus(keyword)}"
    return f"https://www.{domain}/rss/search?q={quote_plus(keyword)}"


def parse_rss_xml(xml_bytes, site, keyword_lower_list):
    """解析 XML 格式 RSS，返回匹配帖子列表"""
    results = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return results

    items = root.findall(".//item")
    if not items:
        # Atom 格式
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", ns)

    for item in items:
        title = ""
        link = ""
        pub_date = ""
        summary = ""

        for child in item:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "title":
                title = unescape((child.text or "").strip())
            elif tag == "link":
                link = (child.text or child.get("href", "")).strip()
            elif tag in ("pubDate", "published", "updated"):
                pub_date = (child.text or "").strip()
            elif tag in ("description", "summary", "content"):
                summary = unescape(re.sub(r"<[^>]+>", "", child.text or ""))

        # 评论数和评论链接
        comments_count = ""
        comments_link = ""
        for child in item:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "comments" and child.text:
                t = child.text.strip()
                if t.isdigit():
                    comments_count = t
                else:
                    comments_link = t
            elif tag == "commentRss" and child.text:
                comments_link = child.text.strip()

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
                "temperature": "",
                "votes": "",
                "needs_browser": site.get("pepper", False) or site.get("proxy", False),
                "matched_keywords": matched,
            })
    return results


def parse_rss_json(json_data, site, keyword_lower_list):
    """解析 rss2json 返回的 JSON"""
    results = []
    for item in json_data.get("items", []):
        title = item.get("title", "")
        link = item.get("link", "")
        pub_date = item.get("pubDate", "")
        summary = re.sub(r"<[^>]+>", "", item.get("description", ""))
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


def scrape_site(site, keywords, keyword_lower_list, timeout=10):
    """抓取单个站点，返回 (site, success, posts, error)"""
    # Pepper 站优先用搜索 RSS（命中率高）
    if site.get("pepper"):
        for kw in keywords:
            search_url = get_pepper_search_url(site, kw)
            if site.get("proxy"):
                data = fetch_via_proxy(search_url, timeout)
                if data:
                    posts = parse_rss_json(data, site, keyword_lower_list)
                    if posts:
                        return site, True, posts, None
            else:
                raw = fetch_url(search_url, timeout)
                if raw:
                    posts = parse_rss_xml(raw, site, keyword_lower_list)
                    if posts:
                        return site, True, posts, None

    # 全站 RSS
    rss_url = site["rss_url"]
    if site.get("proxy"):
        # Cloudflare 站直接走代理
        data = fetch_via_proxy(rss_url, timeout + 5)
        if data:
            posts = parse_rss_json(data, site, keyword_lower_list)
            return site, True, posts, None
        return site, False, [], "proxy_failed"

    # 普通站直连
    raw = fetch_url(rss_url, timeout)
    if raw and (b"<rss" in raw[:200] or b"<feed" in raw[:200] or b"<?xml" in raw[:200]):
        posts = parse_rss_xml(raw, site, keyword_lower_list)
        return site, True, posts, None

    # 回退探测常见 RSS 路径
    for path in RSS_FALLBACK_PATHS:
        fallback_url = f"https://www.{site['domain']}{path}"
        raw = fetch_url(fallback_url, timeout)
        if raw and (b"<rss" in raw[:200] or b"<feed" in raw[:200] or b"<?xml" in raw[:200]):
            posts = parse_rss_xml(raw, site, keyword_lower_list)
            return site, True, posts, None

    return site, False, [], "no_rss"


def search_google_news(site, keywords, timeout=15):
    """Google News RSS 搜索回退，只匹配标题减少噪音"""
    query = quote_plus(f"site:{site['domain']} {' '.join(keywords)}")
    url = f"https://news.google.com/rss/search?q={query}&hl=en"
    raw = fetch_url(url, timeout)
    if not raw:
        return []
    results = []
    try:
        root = ET.fromstring(raw)
        for item in root.findall(".//item"):
            title = unescape((item.findtext("title") or "").strip())
            # 只在标题中匹配关键词，减少 Google News 回退噪音
            title_lower = title.lower()
            matched = [kw for kw in keywords if kw.lower() in title_lower]
            if not matched:
                continue
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            summary = re.sub(r"<[^>]+>", "", item.findtext("description") or "")
            results.append({
                "site": site["name"], "domain": site["domain"],
                "country": site["country"].upper(), "title": title,
                "link": link, "pub_date": pub_date,
                "summary": summary[:500],
                "comments_count": "", "comments_link": "",
                "temperature": "", "votes": "",
                "needs_browser": True,
                "matched_keywords": matched,
                "source": "google_news_fallback",
            })
    except Exception:
        pass
    return results


def main():
    parser = argparse.ArgumentParser(description="Deal 站品牌关键词监测 v4（并发抓取）")
    parser.add_argument("-k", "--keyword", action="append", required=True, help="品牌关键词，可多次传入")
    parser.add_argument("-c", "--countries", default="", help="国家代码过滤，逗号分隔，不传扫全部")
    parser.add_argument("--timeout", type=int, default=10, help="单站请求超时秒数，默认 10")
    parser.add_argument("--output", choices=["json", "csv"], default="json", help="输出格式")
    parser.add_argument("--search-fallback", action="store_true", help="失败站点用 Google News 搜索回退")
    parser.add_argument("--workers", type=int, default=10, help="并发线程数，默认 10")
    args = parser.parse_args()

    keywords = args.keyword
    keyword_lower_list = [kw.lower() for kw in keywords]

    # 过滤国家
    sites = SITES
    if args.countries:
        country_set = set(c.strip().lower() for c in args.countries.split(","))
        sites = [s for s in SITES if s["country"] in country_set]

    print(f"扫描 {len(sites)} 个站点，关键词: {keywords}，并发: {args.workers}", file=sys.stderr)

    all_posts = []
    success_count = 0
    failed_sites = []

    # 并发抓取
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(scrape_site, site, keywords, keyword_lower_list, args.timeout): site
            for site in sites
        }
        for future in as_completed(futures):
            site = futures[future]
            try:
                _, success, posts, error = future.result()
                if success:
                    success_count += 1
                    all_posts.extend(posts)
                    if posts:
                        print(f"  [OK] {site['name']}: {len(posts)} 条匹配", file=sys.stderr)
                else:
                    failed_sites.append(site["domain"])
                    print(f"  [FAIL] {site['name']}: {error}", file=sys.stderr)
            except Exception as e:
                failed_sites.append(site["domain"])
                print(f"  [ERROR] {site['name']}: {e}", file=sys.stderr)

    # Google News 回退
    if args.search_fallback and failed_sites:
        print(f"\nGoogle News 回退 {len(failed_sites)} 个失败站点...", file=sys.stderr)
        fallback_sites = [s for s in sites if s["domain"] in failed_sites]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(search_google_news, site, keywords, args.timeout + 5): site
                for site in fallback_sites
            }
            for future in as_completed(futures):
                site = futures[future]
                try:
                    posts = future.result()
                    if posts:
                        all_posts.extend(posts)
                        failed_sites.remove(site["domain"])
                        success_count += 1
                        print(f"  [回退OK] {site['name']}: {len(posts)} 条", file=sys.stderr)
                except Exception:
                    pass

    # 去重
    seen = set()
    unique = []
    for p in all_posts:
        if p["link"] not in seen:
            seen.add(p["link"])
            unique.append(p)

    # 按时间倒序
    def parse_date(s):
        for fmt in ["%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]:
            try:
                dt = datetime.strptime(s.strip(), fmt)
                # 统一转为 naive datetime，避免 offset-aware vs naive 比较错误
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception:
                pass
        return datetime.min
    unique.sort(key=lambda x: parse_date(x["pub_date"]), reverse=True)

    # 输出
    output = {
        "query": {"keywords": keywords, "countries": args.countries or "all",
                  "generated_at": datetime.now().isoformat(),
                  "search_fallback": args.search_fallback},
        "stats": {"total": len(sites), "success": success_count,
                  "failed": len(failed_sites), "matches": len(unique)},
        "failed_sites": failed_sites,
        "total_matches": len(unique),
        "posts": unique,
    }

    if args.output == "csv":
        import csv
        w = csv.writer(sys.stdout)
        w.writerow(["country", "site", "domain", "title", "link", "pub_date",
                    "comments_count", "temperature", "votes", "needs_browser",
                    "matched_keywords", "summary"])
        for p in unique:
            w.writerow([p["country"], p["site"], p["domain"], p["title"], p["link"],
                        p["pub_date"], p.get("comments_count", ""), p.get("temperature", ""),
                        p.get("votes", ""), p.get("needs_browser", False),
                        "|".join(p["matched_keywords"]), p["summary"][:200]])
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
