---
name: deal-brand-tracker
description: 全球 Deal 站品牌关键词监测工具。输入品牌/产品关键词，自动扫描美国、加拿大、德国、英国、法国、意大利、西班牙、墨西哥、波兰、巴西、澳大利亚等 11 国 60+ deal 站（含 Slickdeals、MyDealz、HotUKDeals、Dealabs、Chollometro、OzBargain 等），输出每个站点的发帖时间、帖子标题、Deal 价格、热度/温度、评论数、点赞/投票数和原帖链接。通过 RSS 批量发现 + 浏览器补全互动数据。当用户需要监测品牌在 deal 站的曝光、竞品 deal 帖追踪、站外 deal 声量统计、某产品在哪些 deal 站被发布过时使用。
---

# Deal 站品牌监测

输入品牌关键词，自动扫描全球 60+ deal 站，输出帖子时间、标题、价格、热度、评论、赞数和链接。

## 工作流程（三步法）

### 第一步：RSS 批量发现（必做）

运行脚本批量抓取所有站点 RSS，按关键词过滤出匹配帖子。

```bash
python scripts/rss_fetch.py -k "品牌词1" -k "品牌词2" -c us,de,uk --timeout 12
```

参数说明：
- `-k` / `--keyword`：品牌关键词，可多次传入（如 `-k anker -k soundcore`）
- `-c` / `--countries`：国家代码过滤，逗号分隔（us,ca,de,uk,fr,it,es,mx,pl,br,au），不传则扫全部
- `--timeout`：单站请求超时秒数，默认 12
- `--output json|csv`：输出格式，默认 JSON

脚本行为：
- **Pepper 网络站点**（Slickdeals/MyDealz/HotUKDeals/Dealabs/Chollometro/Pepper.pl/Promodescuentos/Pelando/Promobit/RedFlagDeals）优先调用搜索 RSS（`/rss/search?q=关键词`），命中率高
- 其他站点拉取全站 RSS 后本地关键词匹配
- 主 RSS 失败时自动回退探测 `/feed/`、`/rss/`、`/rss.xml` 等常见路径
- 输出按发布时间倒序、按链接去重

**将脚本输出的 JSON 保存到临时文件或直接解析使用。**

### 第二步：浏览器补全互动数据（对匹配帖子执行）

RSS 通常只含标题/链接/时间/摘要，**热度、评论数、点赞数需要访问原帖页面提取**。

对第一步输出的每条匹配帖子，用浏览器打开 `link`，提取以下数据：

| 数据项 | 提取位置说明 |
|-------|------------|
| **热度/温度** | Pepper 站页面显示"温度"（如 🔥 120°）或热度值；其他站可能无此字段 |
| **点赞/投票** | Pepper 站显示投票数（如 +58）；Reddit 显示 upvotes；社区型站有 thumbs up/down |
| **评论数** | 页面评论区标题或评论图标旁数字 |
| **Deal 价格** | 帖子标题或正文中的价格信息（如 "$29.99"、"€199"） |
| **原价** | 正文中划掉的原价（如 "$49.99"） |
| **帖子类型** | 热门帖(Hot)/新帖(New)/过期帖(Expired)，Pepper 站有标签 |

**浏览器操作要点**：
- 用 `open_url_in_browser` 打开帖子链接
- 页面加载后用 `take_screenshot` 确认内容
- 互动数据通常在帖子标题下方或侧边栏
- 如遇登录墙，调用 `interaction.request_action`（type=browserControl）请用户完成登录
- 批量帖子可逐个打开提取，不必每个都截图，数据明确即可直接记录

**效率优化**：如果匹配帖子超过 20 条，优先处理 Pepper 网络站和高流量站（Slickdeals/MyDealz/HotUKDeals/Dealabs/Chollometro/Reddit/OzBargain），小型编辑型站互动数据有限可标注"无数据"。

### 第三步：整理输出

按国家分组，使用表格输出。表头固定为：

| 国家 | Deal 站 | 帖子标题 | 发布时间 | Deal 价 | 原价 | 热度/温度 | 评论 | 点赞/投票 | 帖子类型 | 原帖链接 |
|------|--------|---------|---------|--------|------|----------|------|----------|---------|---------|

**输出规则**：
- 按国家分组，国家内按发布时间倒序
- 价格提取不到时填"—"，不要编造
- 互动数据提取不到时填"—"，标注 RSS 仅含基础信息
- 原帖链接必须可直接点击，用 Markdown 链接格式 `[标题](URL)`
- 帖子类型：Hot / New / Expired / 未知
- 如果某站 RSS 抓取失败，在表格下方备注"XX 站 RSS 不可用，建议手动检查"

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

## Pepper 网络站点互动数据提取指南

Pepper 网络（MyDealz/HotUKDeals/Dealabs/Chollometro/Pepper.pl/Promodescuentos/Pelando/Promobit/Slickdeals/RedFlagDeals）页面结构统一：

- **温度/热度**：帖子标题旁的火焰图标 + 数字（如 `🔥 85°`），代表帖子热度
- **投票**：温度下方的点赞/点踩按钮，中间显示净投票数（如 `+42`）
- **评论数**：帖子底部或侧边的评论图标 + 数字
- **帖子状态**：标题旁标签 `HOT` / `NEW` / `EXPIRED`
- **价格**：标题中通常包含 `[品牌] 产品名 - €价格` 格式

提取时优先看帖子标题区（首屏上方），数据集中且明确。

## 参考资源

- `references/deal-sites.md` — 全部 60+ 站点的 RSS 地址、站点类型、互动数据说明完整清单。需要确认某站 RSS 地址或互动数据特性时查阅。

## 注意事项

1. **RSS 不是万能的**：部分小型站点 RSS 可能已失效或返回空，脚本会自动跳过并在 stats 中标记 failed。对 failed 站点，如用户特别关注，可用浏览器手动搜索。
2. **关键词语言适配**：监测非英语国家站点时，建议同时传入当地语言关键词（如德国站加德语词、法国站加法语词），提高匹配率。
3. **多品牌词**：`-k` 可多次传入，脚本对标题+摘要做 OR 匹配，任一关键词命中即收录。
4. **时效**：RSS 通常只返回最近 20-100 条帖子，适合监测近期（通常 7 天内）deal。如需历史数据，需用浏览器站内搜索。
5. **Reddit 扩展**：默认只扫 r/deals，如需特定 subreddit（如 r/buildapcsales），在浏览器阶段补充搜索。
