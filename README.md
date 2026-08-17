# deal-brand-tracker

全球 Deal 站品牌关键词监测工具。输入品牌/产品关键词，扫描 11 国 60+ deal 站，输出帖子时间、标题、Deal 价格、热度、评论数、点赞数和原帖链接。

**不绑定任何特定 AI 平台** —— SKILL.md 是通用指令文档，任何大模型（ChatGPT、Claude、Gemini、Doubao 等）读取后均可按流程执行；也可直接运行 Python 脚本独立使用。

## 支持的站点

覆盖美国、加拿大、德国、英国、法国、意大利、西班牙、墨西哥、波兰、巴西、澳大利亚，包括 Slickdeals、MyDealz、HotUKDeals、Dealabs、Chollometro、OzBargain、Reddit 等 60+ 站点。

## 工作原理

1. **RSS 批量发现** — 拉取各站 RSS，按关键词过滤匹配帖子。Pepper 网络站点优先使用搜索 RSS（`/rss/search?q=关键词`），命中率更高。
2. **补全互动数据** — 对匹配帖子访问原帖页面，提取热度/温度、投票、评论数等 RSS 不含的数据。
3. **结构化输出** — 按国家分组的表格，含 Deal 价、原价、热度、评论、点赞、链接。

## 使用方式

### 方式一：作为 AI 助手的指令文档（推荐）

将 `SKILL.md` 的内容提供给任何 AI 助手，或上传到支持自定义指令/知识文件的平台（ChatGPT Custom GPT、Claude Project、Doubao Skill 等）。助手会自动按三步工作流执行。

### 方式二：直接运行 Python 脚本

```bash
python scripts/rss_fetch.py -k "anker" -k "navimow" -c us,de,uk
```

- `-k` 品牌关键词（可多次传入）
- `-c` 国家代码过滤（us,ca,de,uk,fr,it,es,mx,pl,br,au），不传则扫全部
- `--timeout` 请求超时秒数（默认 12）
- `--output json|csv` 输出格式（默认 JSON）

脚本纯 Python 标准库，无第三方依赖。输出 JSON 后可手动访问帖子链接补全互动数据。

### 方式三：手动参考

直接查阅 `SKILL.md` 中的站点 RSS 速查表，手动请求 RSS 或访问各站站内搜索。

## 安装到 AI 平台

| 平台 | 方式 |
|------|------|
| Doubao | 放入 `.user_skills/deal-brand-tracker/` 目录 |
| ChatGPT Custom GPT | 将 SKILL.md 作为 Knowledge 文件上传 |
| Claude Project | 将 SKILL.md 加入项目文件 |
| 其他助手 | 直接将 SKILL.md 内容作为系统指令/提示词 |

## 文件结构

```
deal-brand-tracker/
├── SKILL.md                  # 通用指令文档（工作流 + 输出规范 + RSS 速查表）
├── README.md                 # 本文件
├── references/
│   └── deal-sites.md         # 60+ 站点完整 RSS 配置大全
└── scripts/
    └── rss_fetch.py          # RSS 抓取与关键词匹配脚本（纯标准库）
```
