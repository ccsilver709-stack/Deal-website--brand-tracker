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
