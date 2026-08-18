---
name: deal-brand-tracker
description: 全球 Deal 站品牌关键词监测工具。输入品牌/产品关键词，自动扫描美国、加拿大、德国、英国、法国、意大利、西班牙、墨西哥、波兰、巴西、澳大利亚等 11 国 60+ deal 站（含 Slickdeals、MyDealz、HotUKDeals、Dealabs、Chollometro、OzBargain 等），输出每个站点的发帖时间、帖子标题、Deal 价格、热度/温度、评论数、点赞/投票数和原帖链接。通过 RSS 批量发现 + 网页补全互动数据。当用户需要监测品牌在 deal 站的曝光、竞品 deal 帖追踪、站外 deal 声量统计、某产品在哪些 deal 站被发布过时使用。
---

# Deal 站品牌监测

输入品牌关键词，扫描全球 60+ deal 站，输出帖子时间、标题、价格、热度、评论、赞数和链接。

> **通用性说明**：本文档不依赖任何特定 AI 平台或工具。有代码执行能力时运行脚本最快；有联网/浏览器能力时可直接访问 RSS 和网页；纯文本环境下按降级方案指导用户操作。

---

## 环境适配（先判断，再执行）

| 你的环境能力 | 执行方式 |
|------------|---------|
| 能运行 Python + 有网络 | **首选**：运行 `scripts/rss_fetch.py` 批量抓取，再按需访问帖子页补全数据 |
| 能联网/发 HTTP 请求但不能跑脚本 | 直接请求各站 RSS URL（见下方站点表），解析 XML 过滤关键词 |
| 有浏览器/网页访问能力 | 访问 Pepper 站搜索页和各站 RSS，手动提取 |
| 纯文本无工具 | 输出检索指令给用户手动执行，或基于已知信息提供站点清单和搜索方法 |

---

## 工作流程（三步法）

### 第一步：RSS 批量发现

#### 方式 A：运行脚本（有 Python 环境时）

```bash
python scripts/rss_fetch.py -k "品牌词1" -k "品牌词2" -c us,de,uk --search-fallback
```

参数：
- `-k` / `--keyword`：品牌关键词，可多次传入（如 `-k anker -k soundcore`）
- `-c` / `--countries`：国家代码过滤，逗号分隔（us,ca,de,uk,fr,it,es,mx,pl,br,au），不传则扫全部
- `--timeout`：单站请求超时秒数，默认 10
- `--output json|csv`：输出格式，默认 JSON
- `--search-fallback`：RSS 失败站点用 Google News 搜索回退（只匹配标题，减少噪音）
- `--workers`：并发线程数，默认 10（全量 62 站 1-2 分钟完成）
- `--date-from` / `--date-to`：**历史时间段搜索**（格式 YYYY-MM-DD）。RSS 只保留最近 7 天帖，指定日期范围后，对无匹配站点自动用 Bing + Google News 限定时间范围搜索历史帖。示例：`--date-from 2026-08-10 --date-to 2026-08-16`

脚本纯 Python 标准库，无第三方依赖，**10 线程并发抓取**。输出 JSON 包含 `posts` 数组，每条含：
- `site/domain/country/title/link/pub_date/summary` — 基础信息
- `comments_count` — 评论数（WordPress 站已自动从 RSS 提取）
- `temperature` — 温度/热度（Pepper 站为空，需第二步补全）
- `votes` — 点赞/投票数（Pepper 站为空，需第二步补全）
- `needs_browser` — `true`=必须浏览器补全，`false`=数据已齐全
- `source` — 数据来源：无此字段=RSS 直连；`date_search_google`/`date_search_bing`=历史时间段搜索回退

**历史时间段搜索示例**（RSS 只保留最近 7 天，查更早的帖用日期范围）：
```bash
python scripts/rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16
```
脚本会先跑 RSS，再对无匹配站点自动用搜索引擎限定时间范围搜索，合并结果输出。

**⚠️ Pepper 站重要说明**：
Slickdeals、HotUKDeals、RedFlagDeals、MyDealz、Dealabs、Chollometro、Promodescuentos、Pepper.pl、Pelando、Promobit 这 10 个 Pepper 网络站是 deal 站流量最大的，但约一半被 Cloudflare 全站 403 保护，纯 Python 脚本直连 RSS 经常失败。
- **能直连的**：MyDealz、Dealabs、Chollometro、Promodescuentos、Pepper.pl（约 5 个，视网络情况波动）
- **被 Cloudflare 挡的**：Slickdeals、HotUKDeals、RedFlagDeals、Pelando、Promobit（约 5 个）
- **解决方案**：加 `--search-fallback` 或 `--date-from/--date-to`，脚本对 RSS 失败的 Pepper 站自动用 Google News 搜索回退，抓搜索引擎缓存结果绕过 Cloudflare。测试验证 anker 限定 8/10-8/16 回退找到 Slickdeals 7 条、HotUKDeals 8 条、RedFlagDeals 3 条。
- **热度/温度**：Pepper 站的🔥温度、投票数、评论数只在帖子页面上，RSS 和搜索引擎都不提供，必须第二步用浏览器打开原帖提取。

#### 方式 B：手动请求 RSS（无脚本环境时）

对每个站点，请求其 RSS URL（见下方"站点 RSS 速查表"），返回的 XML 中：
- 帖子在 `<item>`（RSS）或 `<entry>`（Atom）节点下
- 标题取 `<title>`，链接取 `<link>`，时间取 `<pubDate>` 或 `<published>`，摘要取 `<description>`
- 用关键词在标题+摘要中做不区分大小写的匹配，命中即收录

#### 方式 C：Pepper 站直接搜索（最高精度）

Pepper 网络站点支持站内搜索 RSS，直接返回关键词相关帖子：
```
https://www.<域名>/rss/search?q=<关键词>
```
例如：
- `https://www.mydealz.de/rss/search?q=anker`
- `https://www.hotukdeals.com/rss/search?q=robot+lawn+mower`
- `https://www.dealabs.com/rss/search?q=navimow`

---

### 第二步：自动补全互动数据（必须执行，不得跳过）

脚本输出每条帖子含互动字段：
- `comments_count`：评论数（WordPress 站已自动从 RSS 提取，直接用）
- `temperature`：温度/热度（Pepper 站为空，需浏览器提取）
- `votes`：点赞/投票数（Pepper 站为空，需浏览器提取）
- `needs_browser`：`true`=必须用浏览器打开原帖补全，`false`=数据已齐全可跳过

**对每条 `needs_browser: true` 的帖子，必须用浏览器打开 `link` 提取：**

| 数据项 | 提取位置 |
|-------|---------|
| 热度/温度 | Pepper 站火焰图标 + 数字（如 🔥 120°） |
| 点赞/投票 | Pepper 站净投票数（如 +58）；Reddit 显示 upvotes |
| 评论数 | 评论区图标旁数字（脚本已有 comments_count 则直接用） |
| Deal 价格 | 标题或正文中的价格 |
| 原价 | 正文中划掉的原价 |
| 帖子类型 | Hot / New / Expired |

**浏览器补全操作步骤（逐条执行）：**

1. **筛选**：从脚本输出中挑出 `needs_browser: true` 的帖子（主要是 Pepper 站和 Google 回退结果）
2. **打开链接**：用浏览器打开帖子的 `link` 字段。注意：`source=google_news_fallback` 的链接是 Google News 跳转链，打开后会自动重定向到原帖，等待重定向完成
3. **处理 Cloudflare 验证**：如遇"正在进行安全验证"页面，调用 `interaction.request_action`（type=browserControl）请求用户点击"请验证您是真人"复选框，验证通过后页面自动加载
4. **关闭弹窗**：页面加载后如出现 cookie 同意弹窗，点击"Accept all"或"接受"关闭
5. **提取数据**（按站点类型定位）：

| 站点类型 | 🔥热度/温度 | 点赞/投票 | 评论数 |
|---------|------------|----------|--------|
| Pepper 站（HotUKDeals/MyDealz/Dealabs 等） | 帖子标题旁火焰图标+数字（如 🔥80°） | 温度数字即净投票；或单独的👍👎按钮旁数字 | 评论图标旁数字（如 💬0） |
| RedFlagDeals | 左侧 SCORE 区域（如 +4） | 👍up/👎down 按钮旁数字（如 👍13 👎9） | 分页导航（如 Page 3 of 3）表示评论多 |
| OzBargain | 帖子左侧 +数字（如 +45） | 同上，+up/-down | COMMENTS 区域标题旁或评论条数 |
| Reddit | 帖子上方 upvotes 数 | 同上 | 评论链接旁数字 |

6. **提取价格**：Deal 价格在标题下方大字显示（如 £39.99、$699），原价通常是划掉的小字
7. **填回表格**：把提取到的热度、投票、评论、价格填入对应帖子的输出表格
8. **批量处理策略**：匹配超 20 条时，优先补全 Pepper 高流量站（HotUKDeals/Slickdeals/MyDealz/RedFlagDeals/OzBargain），小站互动数据可填"—"

**实测验证参考**：Anker 测试中，浏览器补全 3 条 Pepper 帖成功——HotUKDeals 提取到 🔥80°+0评论+£39.99；RedFlagDeals 提取到 +4投票(👍13👎9)+多页评论+$65.69；OzBargain 提取到 +45投票+$699。

---

### 第三步：整理输出

按国家分组，使用表格输出。表头固定为：

| 国家 | Deal 站 | 帖子标题 | 发布时间 | Deal 价 | 原价 | 热度/温度 | 评论 | 点赞/投票 | 帖子类型 | 原帖链接 |
|------|--------|---------|---------|--------|------|----------|------|----------|---------|---------|

**输出规则**：
- 按国家分组，国家内按发布时间倒序
- 价格/互动数据提取不到时填"—"，不要编造
- 原帖链接必须可直接点击，用 Markdown 链接格式 `[标题](URL)`
- 帖子类型：Hot / New / Expired / 未知
- 某站 RSS 抓取失败时，在表格下方备注"XX 站 RSS 不可用，建议手动检查"
- 开头先给一句话总结：共扫了 X 站，找到 Y 条匹配，其中 Z 条有完整互动数据

---

## 站点 RSS 速查表

### Pepper 网络（支持搜索 RSS，优先用）

| 国家 | 站点 | 域名 | 搜索 RSS |
|------|------|------|---------|
| 美国 | Slickdeals | slickdeals.net | `https://slickdeals.net/rss/search?q=KEYWORD` |
| 加拿大 | RedFlagDeals | redflagdeals.com | `https://forums.redflagdeals.com/rss/` |
| 德国 | MyDealz | mydealz.de | `https://www.mydealz.de/rss/search?q=KEYWORD` |
| 英国 | HotUKDeals | hotukdeals.com | `https://www.hotukdeals.com/rss/search?q=KEYWORD` |
| 法国 | Dealabs | dealabs.com | `https://www.dealabs.com/rss/search?q=KEYWORD` |
| 西班牙 | Chollometro | chollometro.com | `https://www.chollometro.com/rss/search?q=KEYWORD` |
| 墨西哥 | Promodescuentos | promodescuentos.com | `https://www.promodescuentos.com/rss/search?q=KEYWORD` |
| 波兰 | Pepper.pl | pepper.pl | `https://www.pepper.pl/rss/search?q=KEYWORD` |
| 巴西 | Pelando | pelando.com.br | `https://www.pelando.com.br/rss/search?q=KEYWORD` |
| 巴西 | Promobit | promobit.com.br | `https://www.promobit.com.br/rss/search?q=KEYWORD` |

### 其他主要站点（全站 RSS，本地过滤）

| 国家 | 站点 | 域名 | RSS URL |
|------|------|------|---------|
| 美国 | DealNews | dealnews.com | `https://www.dealnews.com/rss.xml` |
| 美国 | Reddit r/deals | reddit.com | `https://www.reddit.com/r/deals/.rss` |
| 美国 | Hip2Save | hip2save.com | `https://hip2save.com/feed/` |
| 美国 | DansDeals | dansdeals.com | `https://www.dansdeals.com/feed/` |
| 美国 | TechBargains | techbargains.com | `https://www.techbargains.com/rss.xml` |
| 美国 | BensBargains | bensbargains.com | `https://bensbargains.com/feed/` |
| 美国 | DealsPlus | dealsplus.com | `https://www.dealsplus.com/rss` |
| 德国 | Mein-Deal | mein-deal.com | `https://www.mein-deal.com/feed/` |
| 德国 | Dealgott | dealgott.de | `https://www.dealgott.de/feed/` |
| 德国 | DealDoktor | dealdoktor.de | `https://www.dealdoktor.de/feed/` |
| 英国 | LatestDeals | latestdeals.co.uk | `https://www.latestdeals.co.uk/feeds/rss` |
| 法国 | SerialDealer | serialdealer.fr | `https://www.serialdealer.fr/feed/` |
| 澳大利亚 | OzBargain | ozbargain.com.au | `https://www.ozbargain.com.au/rss.xml` |
| 巴西 | Gatry | gatry.com | `https://www.gatry.com/feed/` |

> 完整 60+ 站点清单见 `references/deal-sites.md`（如能读取该文件）。小型站点 RSS 失效时，尝试在域名后加 `/feed/`、`/rss/`、`/rss.xml` 探测。

---

## Pepper 网络互动数据提取指南

Pepper 网络页面结构统一，打开帖子后：

- **温度/热度**：帖子标题旁的火焰图标 + 数字（如 `🔥 85°`）
- **投票**：温度下方的点赞/点踩按钮，中间显示净投票数（如 `+42`）
- **评论数**：帖子底部或侧边的评论图标 + 数字
- **帖子状态**：标题旁标签 `HOT` / `NEW` / `EXPIRED`
- **价格**：标题中通常包含 `[品牌] 产品名 - €价格` 格式

优先看帖子标题区（首屏上方），数据集中且明确。

---

## 国家代码对照

| 代码 | 国家 | 主要站点 |
|------|------|---------|
| us | 美国 | Slickdeals, DealNews, Reddit, Hip2Save, DansDeals |
| ca | 加拿大 | RedFlagDeals, SaveaLoonie |
| de | 德国 | MyDealz, Mein-Deal, Dealgott, DealDoktor |
| uk | 英国 | HotUKDeals, LatestDeals |
| fr | 法国 | Dealabs, SerialDealer |
| it | 意大利 | Scontify, WikiDeal, TuttoTek |
| es | 西班牙 | Chollometro, SuperChollos |
| mx | 墨西哥 | Promodescuentos, Megadescuentos |
| pl | 波兰 | Pepper.pl, HotShops |
| br | 巴西 | Pelando, Promobit, Gatry |
| au | 澳大利亚 | OzBargain |

---

## 注意事项

1. **RSS 不是万能的**：部分小型站点 RSS 可能已失效，脚本会自动跳过。对特别关注的 failed 站点，直接访问网站站内搜索。
2. **关键词语言适配**：监测非英语国家站点时，同时传入当地语言关键词（如德国站加德语词、法国站加法语词），匹配率更高。
3. **多品牌词**：`-k` 可多次传入，对标题+摘要做 OR 匹配，任一命中即收录。
4. **时效**：RSS 通常只返回最近 20-100 条帖子，适合监测近期（通常 7 天内）deal。如需历史数据，用站内搜索。
5. **互动数据自动提取**：WordPress 站（Hip2Save/DansDeals/Mein-Deal 等 20+ 站）评论数已从 RSS 自动提取；Pepper 网络站温度/投票必须浏览器打开页面提取，脚本会用 `needs_browser: true` 标记。
6. **Reddit 扩展**：默认只扫 r/deals，如需特定 subreddit（如 r/buildapcsales），将 RSS URL 替换为 `https://www.reddit.com/r/<sub>/.rss`。
7. **纯文本环境降级**：如果无法访问网络或运行脚本，向用户提供站点清单和搜索 URL 模板，指导用户手动检索后将结果粘贴回来整理。
