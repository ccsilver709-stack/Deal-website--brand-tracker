# Deal 站 RSS 源配置大全

覆盖 11 个国家/地区、60+ deal 站的 RSS feed 配置。脚本会自动按优先级尝试已知 RSS 地址，失败后回退到常见路径探测。

## RSS 路径探测优先级

对每个站点，脚本按以下顺序尝试：
1. 本文件中列出的 `rss_url`（已知可用）
2. 常见路径：`/feed/` → `/rss/` → `/rss.xml` → `/feed.xml` → `/?feed=rss2` → `/feeds/posts/default`
3. 读取站点首页 `<link rel="alternate" type="application/rss+xml">` 自动发现

---

## 美国（25 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| dealnews.com | `https://www.dealnews.com/rss.xml` | 独立编辑型 | 页面有评论数，RSS 不含 |
| slickdeals.net | `https://slickdeals.net/rss/` | 社区型(Pepper) | 帖子有投票/评论，RSS 含部分 |
| dealseek.com | `https://www.dealseek.com/feed/` | 聚合型 | 互动数据有限 |
| techbargains.com | `https://www.techbargains.com/rss.xml` | 编辑型 | 页面有评论 |
| myvipon.com | `https://www.myvipon.com/feed/` | Amazon 折扣 | 互动数据有限 |
| koupon.ai | `https://koupon.ai/feed/` | AI 折扣 | 互动数据有限 |
| dealsofamerica.com | `https://www.dealsofamerica.com/rss.php` | 编辑型 | 互动数据有限 |
| bensbargains.com | `https://bensbargains.com/feed/` | 编辑型 | 页面有评论 |
| freestufffinder.com | `https://freestufffinder.com/feed/` | WordPress | 页面有评论 |
| edealinfo.com | `https://www.edealinfo.com/rss.xml` | 编辑型 | 互动数据有限 |
| 1sale.com | `https://1sale.com/feed/` | 编辑型 | 互动数据有限 |
| dealwiki.com | `https://dealwiki.com/feed/` | 维基型 | 互动数据有限 |
| 21usdeal.com | `https://21usdeal.com/en/feed/` | 华人折扣 | 互动数据有限 |
| ihotoffers.com | `https://www.ihotoffers.com/feed/` | 聚合型 | 互动数据有限 |
| swaggrabber.com | `https://swaggrabber.com/feed/` | WordPress | 页面有评论 |
| shopsale.com | `https://www.shopsale.com/rss.php` | 聚合型 | 互动数据有限 |
| fabulesslyfrugal.com | `https://fabulesslyfrugal.com/feed/` | WordPress | 页面有评论 |
| dansdeals.com | `https://www.dansdeals.com/feed/` | WordPress | 页面有评论/热度 |
| dealsplus.com | `https://www.dealsplus.com/rss` | 社区型 | 帖子有投票/评论 |
| reddit.com | `https://www.reddit.com/r/deals/.rss` | 社区型 | RSS 含评论数/点赞 |
| struggleville.net | `https://www.struggleville.net/feed/` | WordPress | 页面有评论 |
| dealam.com | `https://www.dealam.com/rss.xml` | 编辑型 | 互动数据有限 |
| simplexdeals.com | `https://simplexdeals.com/feed/` | 聚合型 | 互动数据有限 |
| moneysavingmom.com | `https://www.moneysavingmom.com/feed/` | WordPress | 页面有评论 |
| hip2save.com | `https://hip2save.com/feed/` | WordPress | 页面有评论/分享数 |

**Reddit 子版块扩展**：除 r/deals 外，还可追加：
- `https://www.reddit.com/r/buildapcsales/.rss`
- `https://www.reddit.com/r/SingleUseCodes/.rss`
- `https://www.reddit.com/r/AmazonUnder5/.rss`
- 用户指定品牌相关 subreddit 时用 `https://www.reddit.com/r/<sub>/.rss`

---

## 加拿大（2 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| savealoonie.com | `https://www.savealoonie.com/feed/` | WordPress | 页面有评论 |
| redflagdeals.com | `https://forums.redflagdeals.com/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论 |

---

## 德国（10 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| dealgott.de | `https://www.dealgott.de/feed/` | 编辑型 | 互动数据有限 |
| mein-deal.com | `https://www.mein-deal.com/feed/` | 编辑型 | 页面有评论 |
| dealbunny.de | `https://www.dealbunny.de/feed/` | 编辑型 | 互动数据有限 |
| snipz.de | `https://snipz.de/feed/` | 聚合型 | 互动数据有限 |
| monsterdealz.de | `https://www.monsterdealz.de/feed/` | 编辑型 | 互动数据有限 |
| dealdoktor.de | `https://www.dealdoktor.de/feed/` | 编辑型 | 互动数据有限 |
| mydealz.de | `https://www.mydealz.de/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| mytopdeals.net | `https://www.mytopdeals.net/feed/` | 聚合型 | 互动数据有限 |
| sparbote.de | `https://www.sparbote.de/feed/` | 编辑型 | 互动数据有限 |
| dealonkel.de | `https://www.dealonkel.de/feed/` | 编辑型 | 互动数据有限 |

---

## 英国（2 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| hotukdeals.com | `https://www.hotukdeals.com/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| latestdeals.co.uk | `https://www.latestdeals.co.uk/feeds/rss` | 社区型 | 帖子有投票/评论 |

---

## 法国（3 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| dealabs.com | `https://www.dealabs.com/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| serialdealer.fr | `https://www.serialdealer.fr/feed/` | 编辑型 | 互动数据有限 |
| bons-plans-malins.com | `https://www.bons-plans-malins.com/feed/` | WordPress | 页面有评论 |

---

## 意大利（5 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| scontify.net | `https://www.scontify.net/feed/` | 聚合型 | 互动数据有限 |
| bestdiscount.it | `https://www.bestdiscount.it/feed/` | 编辑型 | 互动数据有限 |
| wikideal.it | `https://www.wikideal.it/feed/` | 聚合型 | 互动数据有限 |
| hotshops.pl | `https://www.hotshops.it/feed/` | 聚合型 | 互动数据有限 |
| tuttotek.it | `https://www.tuttotek.it/feed/` | 编辑型 | 页面有评论 |

> 注：hotshops.pl 域名实际为波兰站点，用户列表中同时出现在意大利和波兰。以波兰站 `hotshops.pl` 为准。

---

## 西班牙（8 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| chollometro.com | `https://www.chollometro.com/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| super-chollos.com | `https://www.super-chollos.com/feed/` | 编辑型 | 互动数据有限 |
| cholloterapia.com | `https://www.cholloterapia.com/feed/` | WordPress | 页面有评论 |
| soydechollos.com | `https://www.soydechollos.com/feed/` | 编辑型 | 互动数据有限 |
| michollo.com | `https://www.michollo.com/feed/` | 聚合型 | 互动数据有限 |
| cholloschina.com | `https://www.cholloschina.com/feed/` | 中国折扣 | 互动数据有限 |
| mepicaelchollo.com | `https://www.mepicaelchollo.com/feed/` | WordPress | 页面有评论 |
| nolodejesescapar.com | `https://www.nolodejesescapar.com/feed/` | 编辑型 | 互动数据有限 |

---

## 墨西哥（2 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| promodescuentos.com | `https://www.promodescuentos.com/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| megadescuentos.com | `https://www.megadescuentos.com/feed/` | 编辑型 | 互动数据有限 |

---

## 波兰（2 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| pepper.pl | `https://www.pepper.pl/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| hotshops.pl | `https://www.hotshops.pl/feed/` | 聚合型 | 互动数据有限 |

---

## 巴西（3 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| gatry.com | `https://www.gatry.com/feed/` | 社区型 | 帖子有投票/评论 |
| promobit.com.br | `https://www.promobit.com.br/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |
| pelando.com.br | `https://www.pelando.com.br/rss/` | 社区型(Pepper) | 帖子有热度/投票/评论，RSS 含 |

---

## 澳大利亚（1 站）

| 域名 | RSS Feed URL | 站点类型 | 互动数据说明 |
|------|-------------|---------|------------|
| ozbargain.com.au | `https://www.ozbargain.com.au/rss.xml` | 社区型 | 帖子有投票/评论，RSS 含 |

---

## Pepper 网络站点搜索 RSS（高级用法）

Pepper 网络站点（mydealz/hotukdeals/dealabs/chollometro/pepper.pl/promodescuentos/pelando/promobit/redflagdeals/slickdeals）支持按关键词搜索的 RSS：

```
https://<domain>/rss/search?q=<keyword>
```

示例：
- `https://www.mydealz.de/rss/search?q=anker`
- `https://www.hotukdeals.com/rss/search?q=robot+lawn+mower`
- `https://www.dealabs.com/rss/search?q=navimow`

当用户指定品牌关键词时，对 Pepper 站点优先使用搜索 RSS，命中率远高于全站 RSS 过滤。

## 互动数据获取策略

| 数据类型 | RSS 是否包含 | 获取方式 |
|---------|------------|---------|
| 帖子标题 | 是 | RSS `<title>` |
| 发布时间 | 是 | RSS `<pubDate>` |
| 帖子链接 | 是 | RSS `<link>` |
| 内容摘要 | 是 | RSS `<description>` |
| 评论数 | 部分(Pepper/Reddit) | RSS `<slash:comments>` 或页面抓取 |
| 点赞/投票 | 部分(Pepper/Reddit) | 页面抓取 |
| 热度/温度 | 部分(Pepper) | 页面抓取 |
| 分享数 | 否 | 页面抓取 |

**策略**：RSS 负责批量发现匹配帖子 → 对匹配帖子用浏览器访问原帖提取完整互动数据。
