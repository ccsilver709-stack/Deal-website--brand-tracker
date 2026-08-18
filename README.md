---
title: Deal-scraper
sdk: docker
emoji: 🔍
app_port: 5000
---

# Deal Brand Tracker — Web Application

Scan 60+ deal sites across 13 countries for brand mentions. Input a brand keyword, get deal posts with title, date, price, source, and link.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Install enhanced scraping backends
pip install cloudscraper curl_cffi

# 3. Run the app
python app.py

# 4. Open in browser
# http://localhost:5000
```

## Features

- **RSS Search**: Scan 60+ deal sites via RSS feeds (no API key needed)
- **ScraperAPI Bypass**: Bypass Cloudflare on Pepper network sites (Slickdeals, MyDealz, HotUKDeals, etc.)
- **Country Filter**: Toggle 13 countries individually
- **Date Range**: Filter by publication date
- **Export**: Download results as CSV or JSON
- **Dark/Light Mode**: Auto-adapts to system preference

## Two Search Modes

### 1. RSS Search (default)
Uses `rss_fetch.py` to batch-scan all 60+ sites via RSS feeds. Pure Python standard library, no external dependencies needed. Some Cloudflare-protected sites may return 403.

### 2. ScraperAPI (Cloudflare bypass)
Uses `scraperapi_scraper.py` with ScraperAPI's proxy network to bypass Cloudflare Managed Challenge. Requires a free API key from [scraperapi.com](https://www.scraperapi.com/signup/) (5000 requests/month free).

## Docker Deployment

```bash
docker build -t deal-tracker .
docker run -p 5000:5000 deal-tracker
```

## Architecture

```
deal-tracker-app/
├── app.py                  # Flask backend (API + static serving)
├── static/
│   └── index.html          # Single-page frontend
├── scripts/                # Scraping scripts (from skill package)
│   ├── rss_fetch.py        # RSS batch scraper (60+ sites)
│   ├── scraperapi_scraper.py  # ScraperAPI Cloudflare bypass
│   ├── pepper_scraper_full.py # 6-strategy auto-degradation
│   ├── auto_install.py     # Dependency auto-installer
│   └── requirements.txt   # Script-level dependencies
├── references/
│   └── deal-sites.md       # Complete site list (60+ sites)
├── requirements.txt        # App dependencies
├── Dockerfile              # Container deployment
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve frontend |
| GET | `/api/countries` | List supported countries |
| POST | `/api/search` | RSS search (keywords, countries, date range) |
| POST | `/api/scraperapi` | ScraperAPI search (keyword, api_key, countries) |
| GET | `/api/health` | Health check |

## ScraperAPI Key

Get a free key at https://www.scraperapi.com/signup/ (5000 requests/month). The key is entered in the UI and passed to the backend per-request — it is never stored on the server.

## Covered Sites (60+)

US: Slickdeals, DealNews, Reddit, Hip2Save, DansDeals, TechBargains, BensBargains, DealsPlus, DealCatcher, Dealighted, BradsDeals, 1Sale, DealMoon
CA: RedFlagDeals, SaveaLoonie, SmartCanucks
DE: MyDealz, Mein-Deal, Dealgott, DealDoktor, Sparwelt
UK: HotUKDeals, LatestDeals, DealSpy
FR: Dealabs, SerialDealer, Bons-Plans-Geeks
IT: Scontify, WikiDeal
ES: Chollometro, SuperChollos
MX: Promodescuentos, Megadescuentos
PL: Pepper.pl
BR: Pelando, Promobit, Gatry
AU: OzBargain
IN: FreeKaaMaal, IndiaBargains
NL: Kortingscode
