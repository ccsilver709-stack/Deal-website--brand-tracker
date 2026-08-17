# deal-brand-tracker

全球 Deal 站品牌关键词监测 Skill。输入品牌/产品关键词，自动扫描 11 国 60+ deal 站，输出帖子时间、标题、Deal 价格、热度、评论数、点赞数和原帖链接。

## 支持的站点

覆盖美国、加拿大、德国、英国、法国、意大利、西班牙、墨西哥、波兰、巴西、澳大利亚，包括 Slickdeals、MyDealz、HotUKDeals、Dealabs、Chollometro、OzBargain、Reddit 等。

## 工作原理

1. **RSS 批量发现** — `scripts/rss_fetch.py` 拉取各站 RSS，按关键词过滤匹配帖子。Pepper 网络站点优先使用搜索 RSS。
2. **浏览器补全互动数据** — 对匹配帖子访问原帖，提取热度/温度、投票、评论数等 RSS 不含的数据。
3. **结构化输出** — 按国家分组的表格，含 Deal 价、原价、热度、评论、点赞、链接。

## 安装

将本目录复制到 Doubao Skill 目录下的 `.user_skills/` 中即可。

## 使用

```bash
python scripts/rss_fetch.py -k "anker" -k "navimow" -c us,de,uk
```

- `-k` 品牌关键词（可多次传入）
- `-c` 国家代码过滤（us,ca,de,uk,fr,it,es,mx,pl,br,au）
- `--timeout` 请求超时秒数
- `--output json|csv` 输出格式

## 文件结构

```
deal-brand-tracker/
├── SKILL.md                  # Skill 主文件（工作流 + 输出规范）
├── references/
│   └── deal-sites.md         # 60+ 站点 RSS 配置大全
└── scripts/
    └── rss_fetch.py          # RSS 抓取与关键词匹配脚本
```
