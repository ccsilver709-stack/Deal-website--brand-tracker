# deal-brand-tracker

全球 Deal 站品牌关键词监测。输入品牌词，扫描 11 国 60+ deal 站，输出帖子时间、标题、价格、热度、评论、赞数和链接。

## 快速开始

**Windows 用户：双击 `run.bat`，输入品牌关键词即可。**

其他系统：
```bash
python scripts/run.py
```

按提示输入关键词、可选国家、输出格式，自动出结果。

## 一行命令（熟手用）

```bash
python scripts/rss_fetch.py -k anker -k navimow -c us,de,uk
```

- `-k` 品牌关键词，可多次
- `-c` 国家过滤（us,de,uk,fr...），留空扫全部
- `--output json|csv`
- `--search-fallback` RSS 失败站自动用 Google News 回退
- `--workers` 并发线程数，默认 10

### 查历史时间段的帖

RSS 只保留最近 7 天的帖子。要查更早的历史 deal 帖，用日期范围参数：

```bash
python scripts/rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16
```

脚本会先跑 RSS，再对无匹配站点自动用 Bing + Google News 限定时间范围搜索，合并输出。测试验证：anker 限定 8/10-8/16 找到 30 条，覆盖 Slickdeals/HotUKDeals/RedFlagDeals/LatestDeals/OzBargain 等 8 站。

### Pepper 站推荐用法

Slickdeals、HotUKDeals、MyDealz、Dealabs 等 10 个 Pepper 网络站是流量最大的 deal 站，但约一半被 Cloudflare 保护，纯 RSS 直连经常失败。

**推荐加 `--search-fallback` 或 `--date-from/--date-to`**，脚本会对失败的 Pepper 站自动用搜索引擎回退，抓 Google/Bing 缓存绕过 Cloudflare。

```bash
# 近期帖：加回退参数
python scripts/rss_fetch.py -k anker --search-fallback

# 历史帖：用日期范围
python scripts/rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16
```

Pepper 站的🔥温度、投票数、评论数只在帖子页面上，需要用浏览器打开原帖提取。

## 实测效果

### 全量扫描（anker + --search-fallback）

| 指标 | 数值 |
|------|------|
| 扫描站点 | 62 站 |
| 成功站点 | 45 站（73%） |
| 总匹配 | **154 条** |
| 覆盖国家 | 🇦🇺70 / 🇬🇧42 / 🇨🇦21 / 🇺🇸19 / 🇩🇪2 |

### 历史时间段搜索（anker 8/10-8/16）

过滤后真正在日期范围内的 **27 条**，按站点分布：

| 站点 | 数量 |
|------|------|
| HotUKDeals | 16 条 |
| RedFlagDeals | 3 条 |
| Hip2Save / Dealgott / Deals of America / TechBargains / ShopSale / OzBargain / LatestDeals / Slickdeals | 各 1 条 |

### 浏览器补全后输出示例（带热度/赞/评论）

| 国家 | 站点 | 帖子标题 | Deal价 | 🔥热度 | 👍赞/投票 | 评论 |
|------|------|---------|--------|--------|----------|------|
| 🇬🇧 | HotUKDeals | soundcore P30i Noise Cancelling Earbuds | £19.99 | **🔥78°** | — | **4** |
| 🇬🇧 | HotUKDeals | Anker 100W USB C Charger 3-Port GaN | £39.99 | **🔥80°** | — | **0** |
| 🇺🇸 | Slickdeals | Anker 20W 5-Port Nano Travel Power Adapter | $19.99 | — | **👍16** | **5** |
| 🇬🇧 | LatestDeals | Soundcore Anker P40i ANC Earbuds | £35.98 | — | **👍27** | **0** |
| 🇨🇦 | RedFlagDeals | Anker 737 Power Bank + Charger + Cable Bundle | $65.69 | — | **+4 (👍13👎9)** | **多页** |
| 🇦🇺 | OzBargain | Anker Solix C1000 Power Station 1056Wh | $699 | — | **+45** | 有评论 |
| 🇩🇪 | Mein-Deal | Anker Zolo 4-Port USB-C Ladegerät 50W | €25.97 | — | — | **4** |
| 🇺🇸 | Hip2Save | Anker Wireless Earbuds on Amazon | $19.98 | — | — | **0** |

> WordPress 站（Mein-Deal/Hip2Save/Dealgott 等 20+ 站）评论数脚本自动从 RSS 提取；Pepper 站热度/投票需浏览器打开原帖补全。

## 给 AI 助手用

把 `SKILL.md` 丢给任何 AI 助手（ChatGPT / Claude / Doubao 等），它会按流程自动完成 RSS 抓取 + 互动数据补全 + 表格输出。

## 支持的站点（11 国 62 站）

### 美国（25 站）
DealNews、Slickdeals、DealSeek、TechBargains、MyVipon、Koupon.ai、Deals of America、BensBargains、Free Stuff Finder、eDealInfo、1Sale、DealWiki、21usDeal、iHotOffers、SwagGrabber、ShopSale、Fabulessly Frugal、DansDeals、DealsPlus、Reddit(r/deals)、Struggleville、DealAM、SimplexDeals、Money Saving Mom、Hip2Save

### 加拿大（2 站）
SaveaLoonie、RedFlagDeals

### 德国（10 站）
Dealgott、Mein-Deal、DealBunny、Snipz、MonsterDealz、DealDoktor、MyDealz、MyTopDeals、Sparbote、Dealonkel

### 英国（2 站）
HotUKDeals、LatestDeals

### 法国（3 站）
Dealabs、SerialDealer、Bons Plans Malins

### 意大利（4 站）
Scontify、BestDiscount、WikiDeal、TuttoTek

### 西班牙（8 站）
Chollometro、SuperChollos、Cholloterapia、SoyDeChollos、MiChollo、ChollosChina、MePicaElChollo、NoLoDejesEscapar

### 墨西哥（2 站）
Promodescuentos、Megadescuentos

### 波兰（2 站）
Pepper.pl、HotShops

### 巴西（3 站）
Gatry、Promobit、Pelando

### 澳大利亚（1 站）
OzBargain

> 其中 Slickdeals、RedFlagDeals、MyDealz、HotUKDeals、Dealabs、Chollometro、Promodescuentos、Pepper.pl、Pelando、Promobit 属于 Pepper 网络，支持关键词搜索 RSS，命中率最高。

## 文件说明

```
run.bat              # Windows 双击启动
scripts/run.py       # 交互式入口
scripts/rss_fetch.py # 核心抓取脚本（纯 Python 标准库）
SKILL.md             # AI 助手指令文档
references/deal-sites.md  # 60+ 站点完整 RSS 配置
```
