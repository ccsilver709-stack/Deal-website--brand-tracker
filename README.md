# Deal Brand Tracker

> 全球 Deal 站品牌关键词监测工具 — 输入品牌词，一键扫描 11 国 60+ deal 站，输出帖子时间、标题、价格、热度、评论、赞数和原帖链接。

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## 功能特性

- **11 国 62 站全覆盖**：美国、加拿大、德国、英国、法国、意大利、西班牙、墨西哥、波兰、巴西、澳大利亚
- **纯标准库，零依赖**：核心脚本仅用 Python 内置库，下载即跑，无需 pip install
- **10 线程并发抓取**：全量 62 站 1-2 分钟完成
- **多策略回退**：RSS 直连 → Google News 搜索回退 → Bing 历史搜索 → 浏览器补全
- **历史时间段搜索**：RSS 只保留最近 7 天，指定日期范围自动用搜索引擎查历史帖
- **互动数据补全**：WordPress 站评论数自动提取；Pepper 站热度/投票/评论通过浏览器打开原帖补全
- **AI 助手通用技能**：`SKILL.md` 可被任何 AI 助手（ChatGPT / Claude / Doubao / TRAE 等）直接加载使用

---

## 快速开始

### 方式一：Windows 双击运行

双击 `run.bat`，按提示输入品牌关键词即可。

### 方式二：命令行（推荐）

```bash
# 基础用法：扫描全部站点
python scripts/rss_fetch.py -k anker

# 多关键词 + 指定国家
python scripts/rss_fetch.py -k anker -k navimow -c us,de,uk

# 加搜索引擎回退（推荐，绕过 Cloudflare）
python scripts/rss_fetch.py -k anker --search-fallback

# 查历史时间段的帖
python scripts/rss_fetch.py -k anker --date-from 2026-08-10 --date-to 2026-08-16

# 输出 CSV
python scripts/rss_fetch.py -k anker --output csv
```

### 方式三：交互式入口

```bash
python scripts/run.py
```

按提示输入关键词、国家、输出格式，自动出结果。

---

## 作为 AI 助手技能使用

本项目是一个**通用 AI Skill**，可以被任何支持技能加载的 AI 助手使用。

### 安装方法

1. 下载或克隆本仓库
2. 将整个项目文件夹放到 AI 助手的技能目录下：
   - **TRAE**：`.trae/skills/deal-brand-tracker/`
   - **豆包 / Doubao**：`.doubao/agent_mode/workspace/.skills/deal-brand-tracker/`
   - **其他平台**：放到对应技能扫描目录，或直接将 `SKILL.md` 内容粘贴给 AI 助手
3. AI 助手会自动扫描 `SKILL.md` 的 `name` 和 `description`，在用户提出相关需求时自动加载

### 触发方式

用户用自然语言描述需求即可触发，例如：

> "帮我查下 Anker 上周在 deal 站的帖子"
> "Navimow 在欧洲哪些 deal 站有曝光？"
> "监测一下 soundcore 的站外 deal 声量"

AI 助手会自动：
1. 加载 `deal-brand-tracker` 技能
2. 运行 `scripts/rss_fetch.py` 批量扫描
3. 对被 Cloudflare 拦截的站点用搜索引擎回退补全
4. 对 Pepper 站帖子用浏览器打开原帖提取热度/投票/评论
5. 输出结构化表格

---

## 命令行参数详解

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-k`, `--keyword` | 品牌关键词，可多次传入（如 `-k anker -k soundcore`） | 必填 |
| `-c`, `--countries` | 国家代码过滤，逗号分隔（us,ca,de,uk,fr,it,es,mx,pl,br,au） | 全部 |
| `--timeout` | 单站请求超时秒数 | 10 |
| `--output` | 输出格式：`json` 或 `csv` | json |
| `--search-fallback` | RSS 失败站点用 Google News 搜索回退 | 关闭 |
| `--workers` | 并发线程数 | 10 |
| `--date-from` | 历史搜索起始日期（YYYY-MM-DD） | 无 |
| `--date-to` | 历史搜索结束日期（YYYY-MM-DD） | 无 |

### 输出字段说明

脚本输出 JSON 包含 `posts` 数组，每条帖子含：

| 字段 | 说明 |
|------|------|
| `site` | 站点名称 |
| `domain` | 站点域名 |
| `country` | 国家代码 |
| `title` | 帖子标题 |
| `link` | 原帖链接 |
| `pub_date` | 发布时间 |
| `summary` | 帖子摘要 |
| `comments_count` | 评论数（WordPress 站自动提取） |
| `temperature` | 🔥温度/热度（Pepper 站需浏览器补全） |
| `votes` | 点赞/投票数（Pepper 站需浏览器补全） |
| `needs_browser` | `true`=必须浏览器补全，`false`=数据已齐全 |
| `source` | 数据来源（RSS 直连 / Google 回退 / Bing 回退） |

---

## 工作原理

```
用户输入品牌关键词
        │
        ▼
┌─────────────────────┐
│  RSS 批量发现（第一步）│
│  62 站并发抓取 RSS    │
│  关键词匹配标题+摘要   │
└─────────┬───────────┘
          │
          ├── 成功 → 提取基础数据
          │
          └── 失败（Cloudflare 403）
                    │
                    ▼
          ┌──────────────────┐
          │ 搜索引擎回退       │
          │ Google News / Bing │
          │ 限定站点+时间范围   │
          └─────────┬────────┘
                    │
                    ▼
          ┌──────────────────────┐
          │ 互动数据补全（第二步）  │
          │ needs_browser=true 的  │
          │ 帖子用浏览器打开原帖    │
          │ 提取🔥热度/投票/评论    │
          └─────────┬────────────┘
                    │
                    ▼
              结构化表格输出
```

### Pepper 站说明

Slickdeals、HotUKDeals、RedFlagDeals、MyDealz、Dealabs、Chollometro、Promodescuentos、Pepper.pl、Pelando、Promobit 这 10 个 Pepper 网络站是 deal 站流量最大的，但约一半被 Cloudflare 全站 403 保护。

- **能直连的**：MyDealz、Dealabs、Chollometro、Promodescuentos、Pepper.pl（约 5 个，视网络情况波动）
- **被 Cloudflare 挡的**：Slickdeals、HotUKDeals、RedFlagDeals、Pelando、Promobit（约 5 个）
- **解决方案**：加 `--search-fallback` 或 `--date-from/--date-to`，脚本自动用搜索引擎回退
- **热度/温度**：Pepper 站的🔥温度、投票数、评论数只在帖子页面上，必须用浏览器打开原帖提取

---

## 支持的站点（11 国 62 站）

| 国家 | 站点数 | 代表站点 |
|------|--------|---------|
| 🇺🇸 美国 | 25 | Slickdeals, DealNews, TechBargains, Hip2Save, Deals of America |
| 🇨🇦 加拿大 | 2 | RedFlagDeals, SaveaLoonie |
| 🇩🇪 德国 | 10 | MyDealz, Mein-Deal, Dealgott, DealDoktor |
| 🇬🇧 英国 | 2 | HotUKDeals, LatestDeals |
| 🇫🇷 法国 | 3 | Dealabs, SerialDealer, Bons Plans Malins |
| 🇮🇹 意大利 | 4 | Scontify, BestDiscount, WikiDeal |
| 🇪🇸 西班牙 | 8 | Chollometro, SuperChollos, MiChollo |
| 🇲🇽 墨西哥 | 2 | Promodescuentos, Megadescuentos |
| 🇵🇱 波兰 | 2 | Pepper.pl, HotShops |
| 🇧🇷 巴西 | 3 | Pelando, Promobit, Gatry |
| 🇦🇺 澳大利亚 | 1 | OzBargain |

完整站点 RSS 配置见 [`references/deal-sites.md`](references/deal-sites.md)。

---

## 项目结构

```
deal-brand-tracker/
├── SKILL.md                  # AI 助手指令文档（技能核心定义）
├── README.md                 # 项目说明（本文件）
├── run.bat                   # Windows 双击启动
├── .gitignore                # Git 忽略规则
├── scripts/
│   ├── run.py                # 交互式入口（无需记参数）
│   └── rss_fetch.py          # 核心抓取脚本（纯 Python 标准库）
└── references/
    └── deal-sites.md         # 60+ 站点完整 RSS 配置清单
```

---

## 通用化设计

本技能从设计上保证**任何人、任何环境都能使用**：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无硬编码 API Key | ✅ | 不依赖任何付费 API，纯 RSS + 搜索引擎回退 |
| 零第三方依赖 | ✅ | 核心脚本仅用 Python 标准库，无需 pip install |
| 脚本用相对路径 | ✅ | 全部用 `scripts/xxx.py` 相对路径，不依赖绝对路径 |
| 多环境适配 | ✅ | SKILL.md 含 4 种环境适配方案（Python / HTTP / 浏览器 / 纯文本） |
| 渐进式降级 | ✅ | RSS 失败 → 搜索引擎回退 → 浏览器手动补全，每一步都有替代方案 |
| 无用户私有数据 | ✅ | 代码中不含任何个人信息、密钥或特定配置 |
| 跨平台 | ✅ | Windows / macOS / Linux 均可运行，提供 .bat 和 .py 两种入口 |

### 环境适配表

| 你的环境能力 | 执行方式 |
|------------|---------|
| 能运行 Python + 有网络 | **首选**：运行 `scripts/rss_fetch.py` 批量抓取 |
| 能联网/发 HTTP 请求但不能跑脚本 | 直接请求各站 RSS URL，解析 XML 过滤关键词 |
| 有浏览器/网页访问能力 | 访问 Pepper 站搜索页和各站 RSS，手动提取 |
| 纯文本无工具 | 按 SKILL.md 中的检索指令手动执行 |

---

## 实测效果

### 全量扫描（anker + --search-fallback）

| 指标 | 数值 |
|------|------|
| 扫描站点 | 62 站 |
| 成功站点 | 45 站（73%） |
| 总匹配 | **154 条** |
| 覆盖国家 | 🇦🇺70 / 🇬🇧42 / 🇨🇦21 / 🇺🇸19 / 🇩🇪2 |

### 浏览器补全后输出示例

| 国家 | 站点 | 帖子标题 | Deal价 | 🔥热度 | 👍赞/投票 | 评论 |
|------|------|---------|--------|--------|----------|------|
| 🇬🇧 | HotUKDeals | soundcore P30i Noise Cancelling Earbuds | £19.99 | **🔥78°** | — | **4** |
| 🇬🇧 | HotUKDeals | Anker 100W USB C Charger 3-Port GaN | £39.99 | **🔥80°** | — | **0** |
| 🇺🇸 | Slickdeals | Anker 20W 5-Port Nano Travel Power Adapter | $19.99 | — | **👍16** | **5** |
| 🇨🇦 | RedFlagDeals | Anker 737 Power Bank Bundle | $65.69 | — | **+4** | 多页 |
| 🇦🇺 | OzBargain | Anker Solix C1000 Power Station | $699 | — | **+45** | 有评论 |

---

## 常见问题

**Q: 为什么有些站点抓不到数据？**
A: 约 5 个 Pepper 站被 Cloudflare 全站保护，纯脚本直连会 403。加 `--search-fallback` 参数可通过搜索引擎回退获取结果。

**Q: 为什么 Pepper 站没有热度和投票数？**
A: 🔥温度、投票数、评论数只在帖子详情页上，RSS 和搜索引擎都不提供。需要用浏览器打开原帖链接手动提取，SKILL.md 中有详细的补全步骤。

**Q: 能查多久以前的帖子？**
A: RSS 只保留最近 7 天。查更早的帖用 `--date-from` / `--date-to` 参数，脚本会自动用 Bing + Google News 限定时间范围搜索历史帖。

**Q: 需要安装什么依赖吗？**
A: 不需要。核心脚本 `rss_fetch.py` 纯 Python 标准库编写，Python 3.7+ 即可运行。

---

## License

[MIT](LICENSE) — 自由使用、修改和分发。
