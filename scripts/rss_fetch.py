#!/usr/bin/env python3
"""
Deal 站品牌关键词监测脚本

通过 RSS 批量抓取全球 60+ deal 站的最新帖子，按品牌关键词过滤，输出匹配结果。
对 Pepper 网络站点优先使用搜索 RSS，其他站点拉取全站 RSS 后本地过滤。

用法:
    python rss_fetch.py --keyword "anker" --keyword "navimow"
    python rss_fetch.py --keyword "mammotion" --countries us,de,uk
    python rss_fetch.py --keyword "robot lawn mower" --output json
    python rss_fetch.py --keyword "toocki" --max-items 200 --timeout 15

输出: JSON 到 stdout，包含匹配帖子列表。
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
from urllib.parse import quote_plus

# ============================================================
# 站点配置：域名 -> {country, name, rss_url, pepper(bool), search_rss模板}
# pepper=True 的站点支持 /rss/search?q=keyword 搜索 RSS
# ============================================================
SITES = [
    # 美国
    {"domain": "dealnews.com", "country": "us", "name": "DealNews", "rss_url": "https://www.dealnews.com/rss.xml", "pepper": False},
    {"domain": "slickdeals.net", "country": "us", "name": "Slickdeals", "rss_url": "https://slickdeals.net/rss/", "pepper": True},
    {"domain": "dealseek.com", "country": "us", "name": "DealSeek", "rss_url": "https://www.dealseek.com/feed/", "pepper": False},
    {"domain": "techbargains.com", "country": "us", "name": "TechBargains", "rss_url": "https://www.techbargains.com/rss.xml", "pepper": False},
    {"domain": "myvipon.com", "country": "us", "name": "MyVipon", "rss_url": "https://www.myvipon.com/feed/", "pepper": False},
    {"domain": "koupon.ai", "country": "us", "name": "Koupon.ai", "rss_url": "https://koupon.ai/feed/", "pepper": False},
    {"domain": "dealsofamerica.com", "country": "us", "name": "Deals of America", "rss_url": "https://www.dealsofamerica.com/rss.php", "pepper": False},
    {"domain": "bensbargains.com", "country": "us", "name": "BensBargains", "rss_url": "https://bensbargains.com/feed/", "pepper": False},
    {"domain": "freestufffinder.com", "country": "us", "name": "Free Stuff Finder", "rss_url": "https://freestufffinder.com/feed/", "pepper": False},
    {"domain": "edealinfo.com", "country": "us", "name": "eDealInfo", "rss_url": "https://www.edealinfo.com/rss.xml", "pepper": False},
    {"domain": "1sale.com", "country": "us", "name": "1Sale", "rss_url": "https://1sale.com/feed/", "pepper": False},
    {"domain": "dealwiki.com", "country": "us", "name": "DealWiki", "rss_url": "https://dealwiki.com/feed/", "pepper": False},
    {"domain": "21usdeal.com", "country": "us", "name": "21usDeal", "rss_url": "https://21usdeal.com/en/feed/", "pepper": False},
    {"domain": "ihotoffers.com", "country": "us", "name": "iHotOffers", "rss_url": "https://www.ihotoffers.com/feed/", "pepper": False},
    {"domain": "swaggrabber.com", "country": "us", "name": "SwagGrabber", "rss_url": "https://swaggrabber.com/feed/", "pepper": False},
    {"domain": "shopsale.com", "country": "us", "name": "ShopSale", "rss_url": "https://www.shopsale.com/rss.php", "pepper": False},
    {"domain": "fabulesslyfrugal.com", "country": "us", "name": "Fabulessly Frugal", "rss_url": "https://fabulesslyfrugal.com/feed/", "pepper": False},
    {"domain": "dansdeals.com", "country": "us", "name": "DansDeals", "rss_url": "https://www.dansdeals.com/feed/", "pepper": False},
    {"domain": "dealsplus.com", "country": "us", "name": "DealsPlus", "rss_url": "https://www.dealsplus.com/rss", "pepper": False},
    {"domain": "reddit.com", "country": "us", "name": "Reddit r/deals", "rss_url": "https://www.reddit.com/r/deals/.rss", "pepper": False},
    {"domain": "struggleville.net", "country": "us", "name": "Struggleville", "rss_url": "https://www.struggleville.net/feed/", "pepper": False},
    {"domain": "dealam.com", "country": "us", "name": "DealAM", "rss_url": "https://www.dealam.com/rss.xml", "pepper": False},
    {"domain": "simplexdeals.com", "country": "us", "name": "SimplexDeals", "rss_url": "https://simplexdeals.com/feed/", "pepper": False},
    {"domain": "moneysavingmom.com", "country": "us", "name": "Money Saving Mom", "rss_url": "https://www.moneysavingmom.com/feed/", "pepper": False},
    {"domain": "hip2save.com", "country": "us", "name": "Hip2Save", "rss_url": "https://hip2save.com/feed/", "pepper": False},
    # 加拿大
    {"domain": "savealoonie.com", "country": "ca", "name": "SaveaLoonie", "rss_url": "https://www.savealoonie.com/feed/", "pepper": False},
    {"domain": "redflagdeals.com", "country": "ca", "name": "RedFlagDeals", "rss_url": "https://forums.redflagdeals.com/rss/", "pepper": True},
    # 德国
    {"domain": "dealgott.de", "country": "de", "name": "Dealgott", "rss_url": "https://www.dealgott.de/feed/", "pepper": False},
    {"domain": "mein-deal.com", "country": "de", "name": "Mein-Deal", "rss_url": "https://www.mein-deal.com/feed/", "pepper": False},
    {"domain": "dealbunny.de", "country": "de", "name": "DealBunny", "rss_url": "https://www.dealbunny.de/feed/", "pepper": False},
    {"domain": "snipz.de", "country": "de", "name": "Snipz", "rss_url": "https://snipz.de/feed/", "pepper": False},
    {"domain": "monsterdealz.de", "country": "de", "name": "MonsterDealz", "rss_url": "https://www.monsterdealz.de/feed/", "pepper": False},
    {"domain": "dealdoktor.de", "country": "de", "name": "DealDoktor", "rss_url": "https://www.dealdoktor.de/feed/", "pepper": False},
    {"domain": "mydealz.de", "country": "de", "name": "MyDealz", "rss_url": "https://www.mydealz.de/rss/", "pepper": True},
    {"domain": "mytopdeals.net", "country": "de", "name": "MyTopDeals", "rss_url": "https://www.mytopdeals.net/feed/", "pepper": False},
    {"domain": "sparbote.de", "country": "de", "name": "Sparbote", "rss_url": "https://www.sparbote.de/feed/", "pepper": False},
    {"domain": "dealonkel.de", "country": "de", "name": "Dealonkel", "rss_url": "https://www.dealonkel.de/feed/", "pepper": False},
    # 英国
    {"domain": "hotukdeals.com", "country": "uk", "name": "HotUKDeals", "rss_url": "https://www.hotukdeals.com/rss/", "pepper": True},
    {"domain": "latestdeals.co.uk", "country": "uk", "name": "LatestDeals", "rss_url": "https://www.latestdeals.co.uk/feeds/rss", "pepper": False},
    # 法国
    {"domain": "dealabs.com", "country": "fr", "name": "Dealabs", "rss_url": "https://www.dealabs.com/rss/", "pepper": True},
    {"domain": "serialdealer.fr", "country": "fr", "name": "SerialDealer", "rss_url": "https://www.serialdealer.fr/feed/", "pepper": False},
    {"domain": "bons-plans-malins.com", "country": "fr", "name": "Bons Plans Malins", "rss_url": "https://www.bons-plans-malins.com/feed/", "pepper": False},
    # 意大利
    {"domain": "scontify.net", "country": "it", "name": "Scontify", "rss_url": "https://www.scontify.net/feed/", "pepper": False},
    {"domain": "bestdiscount.it", "country": "it", "name": "BestDiscount", "rss_url": "https://www.bestdiscount.it/feed/", "pepper": False},
    {"domain": "wikideal.it", "country": "it", "name": "WikiDeal", "rss_url": "https://www.wikideal.it/feed/", "pepper": False},
    {"domain": "tuttotek.it", "country": "it", "name": "TuttoTek", "rss_url": "https://www.tuttotek.it/feed/", "pepper": False},
    # 西班牙
    {"domain": "chollometro.com", "country": "es", "name": "Chollometro", "rss_url": "https://www.chollometro.com/rss/", "pepper": True},
    {"domain": "super-chollos.com", "country": "es", "name": "SuperChollos", "rss_url": "https://www.super-chollos.com/feed/", "pepper": False},
    {"domain": "cholloterapia.com", "country": "es", "name": "Cholloterapia", "rss_url": "https://www.cholloterapia.com/feed/", "pepper": False},
    {"domain": "soydechollos.com", "country": "es", "name": "SoyDeChollos", "rss_url": "https://www.soydechollos.com/feed/", "pepper": False},
    {"domain": "michollo.com", "country": "es", "name": "MiChollo", "rss_url": "https://www.michollo.com/feed/", "pepper": False},
    {"domain": "cholloschina.com", "country": "es", "name": "ChollosChina", "rss_url": "https://www.cholloschina.com/feed/", "pepper": False},
    {"domain": "mepicaelchollo.com", "country": "es", "name": "MePicaElChollo", "rss_url": "https://www.mepicaelchollo.com/feed/", "pepper": False},
    {"domain": "nolodejesescapar.com", "country": "es", "name": "NoLoDejesEscapar", "rss_url": "https://www.nolodejesescapar.com/feed/", "pepper": False},
    # 墨西哥
    {"domain": "promodescuentos.com", "country": "mx", "name": "Promodescuentos", "rss_url": "https://www.promodescuentos.com/rss/", "pepper": True},
    {"domain": "megadescuentos.com", "country": "mx", "name": "Megadescuentos", "rss_url": "https://www.megadescuentos.com/feed/", "pepper": False},
    # 波兰
    {"domain": "pepper.pl", "country": "pl", "name": "Pepper.pl", "rss_url": "https://www.pepper.pl/rss/", "pepper": True},
    {"domain": "hotshops.pl", "country": "pl", "name": "HotShops", "rss_url": "https://www.hotshops.pl/feed/", "pepper": False},
    # 巴西
    {"domain": "gatry.com", "country": "br", "name": "Gatry", "rss_url": "https://www.gatry.com/feed/", "pepper": False},
    {"domain": "promobit.com.br", "country": "br", "name": "Promobit", "rss_url": "https://www.promobit.com.br/rss/", "pepper": True},
    {"domain": "pelando.com.br", "country": "br", "name": "Pelando", "rss_url": "https://www.pelando.com.br/rss/", "pepper": True},
    # 澳大利亚
    {"domain": "ozbargain.com.au", "country": "au", "name": "OzBargain", "rss_url": "https://www.ozbargain.com.au/rss.xml", "pepper": False},
]

# RSS 路径回退列表（当主 RSS 失败时尝试）
RSS_FALLBACK_PATHS = ["/feed/", "/rss/", "/rss.xml", "/feed.xml", "/?feed=rss2", "/feeds/posts/default"]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_url(url, timeout=12):
    """抓取 URL 内容，失败返回 None"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
        pass
    return None


def parse_rss(xml_bytes, site, keyword_lower_list):
    """
    解析 RSS/Atom XML，返回匹配关键词的帖子列表。
    每个帖子: {site, domain, country, title, link, pub_date, summary, comments}
    """
    results = []
    if not xml_bytes:
        return results

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return results

    # 处理 RSS 2.0 和 Atom
    # RSS 2.0: rss/channel/item
    # Atom: feed/entry
    items = root.findall(".//item")
    if not items:
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", ns)

    for item in items:
        # 标题
        title_el = item.find("title")
        title = unescape(title_el.text.strip()) if title_el is not None and title_el.text else ""

        # 链接
        link = ""
        link_el = item.find("link")
        if link_el is not None:
            if link_el.text:
                link = link_el.text.strip()
            elif link_el.get("href"):
                link = link_el.get("href").strip()

        # 发布时间
        pub_date = ""
        for tag in ["pubDate", "published", "updated", "date"]:
            el = item.find(tag)
            if el is not None and el.text:
                pub_date = el.text.strip()
                break

        # 摘要/内容
        summary = ""
        for tag in ["description", "summary", "content", "encoded"]:
            el = item.find(tag)
            if el is not None and el.text:
                summary = unescape(re.sub(r"<[^>]+>", "", el.text)).strip()
                break
        # content:encoded (命名空间)
        if not summary:
            for child in item:
                if child.tag.endswith("encoded") and child.text:
                    summary = unescape(re.sub(r"<[^>]+>", "", child.text)).strip()
                    break

        # 评论数 (slash:comments)
        comments = ""
        for child in item:
            if child.tag.endswith("comments") and child.text:
                comments = child.text.strip()
                break

        # 关键词匹配：标题 + 摘要，不区分大小写
        text_blob = (title + " " + summary).lower()
        matched_keywords = [kw for kw in keyword_lower_list if kw in text_blob]

        if matched_keywords:
            results.append({
                "site": site["name"],
                "domain": site["domain"],
                "country": site["country"].upper(),
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "summary": summary[:500] if summary else "",
                "comments_rss": comments,
                "matched_keywords": matched_keywords,
            })

    return results


def get_rss_for_site(site, keywords):
    """
    获取站点 RSS 内容。
    - Pepper 站点：优先用搜索 RSS（第一个关键词）
    - 其他站点：用全站 RSS
    失败时尝试回退路径。
    """
    # Pepper 站点用搜索 RSS
    if site["pepper"] and keywords:
        search_url = f"https://www.{site['domain']}/rss/search?q={quote_plus(keywords[0])}"
        content = fetch_url(search_url)
        if content:
            return content, search_url

    # 主 RSS
    content = fetch_url(site["rss_url"])
    if content:
        return content, site["rss_url"]

    # 回退路径探测
    for path in RSS_FALLBACK_PATHS:
        fallback_url = f"https://www.{site['domain']}{path}"
        content = fetch_url(fallback_url)
        if content:
            return content, fallback_url

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Deal 站品牌关键词 RSS 监测")
    parser.add_argument("--keyword", "-k", action="append", required=True,
                        help="品牌关键词，可多次指定（如 -k anker -k navimow）")
    parser.add_argument("--countries", "-c", default=None,
                        help="过滤国家代码，逗号分隔（如 us,de,uk）。默认全部国家。")
    parser.add_argument("--max-items", type=int, default=100,
                        help="每个站点最多解析的帖子数（默认 100）")
    parser.add_argument("--timeout", type=int, default=12,
                        help="单个请求超时秒数（默认 12）")
    parser.add_argument("--output", choices=["json", "csv"], default="json",
                        help="输出格式（默认 json）")
    args = parser.parse_args()

    keywords = [kw.strip().lower() for kw in args.keyword if kw.strip()]
    if not keywords:
        print("错误：至少需要一个关键词", file=sys.stderr)
        sys.exit(1)

    # 国家过滤
    countries = None
    if args.countries:
        countries = set(c.strip().lower() for c in args.countries.split(",") if c.strip())

    # 筛选站点
    sites_to_check = SITES
    if countries:
        sites_to_check = [s for s in SITES if s["country"] in countries]

    all_matches = []
    site_stats = {"total": len(sites_to_check), "success": 0, "failed": 0, "matches": 0}

    for site in sites_to_check:
        content, used_url = get_rss_for_site(site, keywords)
        if content is None:
            site_stats["failed"] += 1
            continue

        site_stats["success"] += 1
        matches = parse_rss(content, site, keywords)
        if matches:
            # 限制每站数量
            matches = matches[:args.max_items]
            all_matches.extend(matches)
            site_stats["matches"] += len(matches)

    # 按发布时间倒序（能解析的优先，不能解析的排后面）
    def sort_key(item):
        date_str = item.get("pub_date", "")
        try:
            # 尝试解析常见日期格式
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S GMT"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.timestamp()
                except ValueError:
                    continue
        except Exception:
            pass
        return 0

    all_matches.sort(key=sort_key, reverse=True)

    # 去重（按链接）
    seen_links = set()
    unique_matches = []
    for m in all_matches:
        link = m.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            unique_matches.append(m)
        elif not link:
            unique_matches.append(m)

    output = {
        "query": {
            "keywords": args.keyword,
            "countries": args.countries or "all",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "stats": site_stats,
        "total_matches": len(unique_matches),
        "posts": unique_matches,
    }

    if args.output == "csv":
        # 简易 CSV 输出
        import csv
        writer = csv.writer(sys.stdout)
        writer.writerow(["country", "site", "domain", "title", "link", "pub_date", "comments_rss", "matched_keywords", "summary"])
        for p in unique_matches:
            writer.writerow([
                p["country"], p["site"], p["domain"], p["title"],
                p["link"], p["pub_date"], p["comments_rss"],
                "|".join(p["matched_keywords"]), p["summary"][:200],
            ])
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
