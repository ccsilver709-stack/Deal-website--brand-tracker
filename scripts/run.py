#!/usr/bin/env python3
"""
Deal 站品牌监测 - 交互式入口
直接运行，输入品牌关键词即可，无需记命令行参数。
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RSS_SCRIPT = os.path.join(SCRIPT_DIR, "rss_fetch.py")


def main():
    print("=" * 50)
    print("  Deal 站品牌关键词监测")
    print("=" * 50)
    print()

    # 关键词
    keyword_input = input("输入品牌关键词（多个用空格分隔）: ").strip()
    if not keyword_input:
        print("错误：关键词不能为空")
        sys.exit(1)
    keywords = keyword_input.split()

    # 国家过滤
    print()
    print("国家代码（留空=全部）: us,ca,de,uk,fr,it,es,mx,pl,br,au")
    countries = input("指定国家（逗号分隔，或直接回车扫全部）: ").strip()

    # 输出格式
    print()
    fmt = input("输出格式 json/csv（默认 json）: ").strip().lower()
    if fmt not in ("json", "csv"):
        fmt = "json"

    # 组装命令
    cmd = [sys.executable, RSS_SCRIPT]
    for kw in keywords:
        cmd.extend(["-k", kw])
    if countries:
        cmd.extend(["-c", countries])
    cmd.extend(["--output", fmt])

    print()
    print(f"正在扫描 {len(keywords)} 个关键词...")
    print("-" * 50)

    # 运行脚本，输出直接透传
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
