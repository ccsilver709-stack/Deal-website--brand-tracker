#!/usr/bin/env python3
"""
Deal Brand Tracker - Auto Dependency Installer

Automatically detects and installs all required Python dependencies
for the Pepper Network Deal Scraper. Safe to run multiple times.

Usage:
  python scripts/auto_install.py
"""

import subprocess
import sys
import importlib
import os


# ═══════════════════════════════════════════════════════════════════════
#  Dependency Definitions
# ═══════════════════════════════════════════════════════════════════════

DEPENDENCIES = [
    {
        "package": "cloudscraper",
        "import_name": "cloudscraper",
        "strategy": "策略0 直连RSS + 策略3 Google缓存",
        "required": False,
        "pip_name": "cloudscraper",
    },
    {
        "package": "curl_cffi",
        "import_name": "curl_cffi",
        "strategy": "策略0 直连RSS + 策略3 TLS指纹",
        "required": False,
        "pip_name": "curl_cffi",
    },
    {
        "package": "undetected-chromedriver",
        "import_name": "undetected_chromedriver",
        "strategy": "策略1 浏览器绕过",
        "required": False,
        "pip_name": "undetected-chromedriver",
    },
    {
        "package": "selenium",
        "import_name": "selenium",
        "strategy": "策略1 浏览器驱动",
        "required": False,
        "pip_name": "selenium",
    },
    {
        "package": "requests",
        "import_name": "requests",
        "strategy": "策略0 直连RSS + 策略4 第三方API",
        "required": False,
        "pip_name": "requests",
    },
    {
        "package": "beautifulsoup4",
        "import_name": "bs4",
        "strategy": "HTML解析增强（可选）",
        "required": False,
        "pip_name": "beautifulsoup4",
    },
]


# ═══════════════════════════════════════════════════════════════════════
#  Installation Logic
# ═══════════════════════════════════════════════════════════════════════

def is_installed(import_name):
    """Check if a package is already installed."""
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def pip_install(package_name):
    """Install a package via pip, trying with and without --break-system-packages."""
    # Try with --break-system-packages first (Linux)
    cmd = [sys.executable, "-m", "pip", "install", package_name, "--break-system-packages"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        return True, None
    
    # Fallback: try without --break-system-packages (macOS/Windows/venv)
    cmd = [sys.executable, "-m", "pip", "install", package_name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        return True, None
    
    return False, result.stderr.strip()[-200:] if result.stderr else "Unknown error"


def check_chrome():
    """Check if Chrome/Chromium is installed on the system."""
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/local/bin/chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            return True, path
    
    # Try which command
    try:
        result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except Exception:
        pass
    
    try:
        result = subprocess.run(["which", "chromium-browser"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except Exception:
        pass
    
    return False, None


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print()
    print("=" * 60)
    print("  Deal Brand Tracker - Auto Dependency Installer")
    print("=" * 60)
    print()
    
    installed_count = 0
    skipped_count = 0
    failed_count = 0
    
    for dep in DEPENDENCIES:
        pkg = dep["package"]
        imp = dep["import_name"]
        strategy = dep["strategy"]
        
        if is_installed(imp):
            print(f"  ✓ {pkg:30s} already installed ({strategy})")
            skipped_count += 1
        else:
            print(f"  → Installing {pkg} ({strategy})...", end=" ", flush=True)
            success, error = pip_install(dep["pip_name"])
            
            if success:
                print("DONE")
                installed_count += 1
            else:
                print(f"FAILED")
                print(f"    Error: {error[:100]}" if error else "    Unknown error")
                print(f"    → 脚本运行时会自动跳过{strategy}")
                failed_count += 1
    
    # Check Chrome
    print()
    print("  --- Chrome Browser Check ---")
    chrome_ok, chrome_path = check_chrome()
    if chrome_ok:
        print(f"  ✓ Chrome/Chromium found: {chrome_path}")
        print(f"    → 策略1 (undetected-chromedriver) 可用")
    else:
        print(f"  ✗ Chrome/Chromium not found")
        print(f"    → 策略1 (undetected-chromedriver) 不可用，脚本会自动跳过")
        print(f"    → 如需使用策略1，请安装 Chrome:")
        print(f"       Ubuntu:  apt install chromium-browser")
        print(f"       macOS:   brew install --cask google-chrome")
        print(f"       或从 https://www.google.com/chrome/ 下载")
    
    # Summary
    print()
    print("=" * 60)
    print(f"  Summary: {skipped_count} already installed, {installed_count} newly installed, {failed_count} failed")
    print("=" * 60)
    
    if failed_count > 0:
        print()
        print("  Note: Failed dependencies are NOT fatal.")
        print("  The scraper script will automatically skip strategies")
        print("  whose dependencies are missing and fall back to alternatives.")
        print()
        print("  Minimal install for basic functionality:")
        print("    pip install cloudscraper curl_cffi")
    
    print()
    print("  Ready to run:")
    print("    # Pepper 站 Cloudflare 绕过抓取")
    print("    python scripts/pepper_scraper_full.py -k <keyword> --strategy auto")
    print()
    print("    # 全部 60+ 站 RSS 批量抓取")
    print("    python scripts/rss_fetch.py -k <keyword> --search-fallback")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
