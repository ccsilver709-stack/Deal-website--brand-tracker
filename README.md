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

## 给 AI 助手用

把 `SKILL.md` 丢给任何 AI 助手（ChatGPT / Claude / Doubao 等），它会按流程自动完成 RSS 抓取 + 互动数据补全 + 表格输出。

## 文件说明

```
run.bat              # Windows 双击启动
scripts/run.py       # 交互式入口
scripts/rss_fetch.py # 核心抓取脚本（纯 Python 标准库）
SKILL.md             # AI 助手指令文档
references/deal-sites.md  # 60+ 站点完整 RSS 配置
```
