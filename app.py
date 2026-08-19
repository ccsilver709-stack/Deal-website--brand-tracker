#!/usr/bin/env python3
"""
Deal Brand Tracker — Web Application
Flask backend that wraps the deal-brand-tracker skill scripts.

Run:  python app.py
Open: http://localhost:5000
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, send_from_directory, jsonify, request

app = Flask(__name__, static_folder="static", static_url_path="")

SCRIPTS_DIR = Path(__file__).parent / "scripts"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ─── Countries ───────────────────────────────────────────────────────────────

COUNTRIES = [
    {"code": "us", "name": "United States", "sites": 17},
    {"code": "ca", "name": "Canada", "sites": 3},
    {"code": "de", "name": "Germany", "sites": 5},
    {"code": "uk", "name": "United Kingdom", "sites": 3},
    {"code": "fr", "name": "France", "sites": 3},
    {"code": "it", "name": "Italy", "sites": 2},
    {"code": "es", "name": "Spain", "sites": 2},
    {"code": "mx", "name": "Mexico", "sites": 2},
    {"code": "pl", "name": "Poland", "sites": 1},
    {"code": "br", "name": "Brazil", "sites": 4},
    {"code": "au", "name": "Australia", "sites": 1},
    {"code": "in", "name": "India", "sites": 2},
    {"code": "nl", "name": "Netherlands", "sites": 1},
]


# ─── Date Filtering ──────────────────────────────────────────────────────────

def filter_posts_by_date(posts, date_from, date_to):
    """Post-filter results by date range. Handles various date formats.
    Posts without a parseable date are KEPT (not excluded) when date filter is active."""
    if not date_from and not date_to:
        return posts

    def parse_d(d):
        if not d:
            return None
        d = d.strip()
        for fmt in ("%Y-%m-%d %H:%M %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d",
                     "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
                     "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(d, fmt)
                # Normalize to naive UTC for comparison
                if dt.tzinfo is not None:
                    dt = dt.astimezone(tz=None).replace(tzinfo=None)
                return dt
            except (ValueError, TypeError):
                continue
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            return dt
        except (ValueError, AttributeError):
            return None

    d_from = parse_d(date_from) if date_from else None
    d_to = parse_d(date_to) if date_to else None
    if d_to:
        d_to = d_to.replace(hour=23, minute=59, second=59)

    filtered = []
    for p in posts:
        # Try pub_date_parsed first (already normalized), then pub_date
        pd = parse_d(p.get("pub_date_parsed") or "")
        if pd is None:
            pd = parse_d(p.get("pub_date") or "")
        # If post has no parseable date → keep it (don't exclude by date filter)
        if pd is None:
            filtered.append(p)
            continue
        if d_from and pd < d_from:
            continue
        if d_to and pd > d_to:
            continue
        filtered.append(p)
    return filtered


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/countries")
def get_countries():
    return jsonify({"countries": COUNTRIES})


@app.route("/api/search", methods=["POST"])
def search():
    """
    Run rss_fetch.py with the given parameters.
    Expected JSON body:
      {
        "keywords": ["anker"],           # required, array of brand keywords
        "countries": ["us","de","uk"],    # optional, empty = all
        "date_from": "2026-08-10",        # optional, YYYY-MM-DD
        "date_to": "2026-08-16",          # optional, YYYY-MM-DD
      }
    """
    data = request.get_json(force=True)
    keywords = data.get("keywords", [])
    if not keywords:
        return jsonify({"error": "At least one keyword is required"}), 400

    countries = data.get("countries", [])
    date_from = data.get("date_from", "")
    date_to = data.get("date_to", "")

    # Build command — optimized for speed
    cmd = [sys.executable, str(SCRIPTS_DIR / "rss_fetch.py")]
    for kw in keywords:
        cmd += ["-k", kw]
    if countries:
        cmd += ["-c", ",".join(countries)]
    if date_from:
        cmd += ["--date-from", date_from]
    if date_to:
        cmd += ["--date-to", date_to]
    cmd += ["--timeout", "5", "--workers", "30", "--search-fallback", "--output", "json"]

    # Output to temp file
    job_id = str(uuid.uuid4())[:8]
    output_file = RESULTS_DIR / f"search_{job_id}.json"
    cmd += ["--output-file", str(output_file)]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(SCRIPTS_DIR)
        )
        if result.returncode != 0:
            return jsonify({
                "error": "Script execution failed",
                "stderr": result.stderr[-2000:] if result.stderr else ""
            }), 500

        # Read results
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                results = json.load(f)
            # Clean up temp file
            output_file.unlink(missing_ok=True)
            # Apply date filter (rss_fetch.py doesn't filter internally)
            posts = results.get("posts", [])
            if date_from or date_to:
                posts = filter_posts_by_date(posts, date_from, date_to)
            return jsonify({
                "ok": True,
                "posts": posts,
                "stats": results.get("stats", {}),
                "log": result.stdout[-3000:] if result.stdout else ""
            })
        else:
            # Script may have printed JSON to stdout
            return jsonify({
                "ok": True,
                "posts": [],
                "log": result.stdout[-3000:] if result.stdout else "No output"
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Search timed out (120s limit)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scraperapi", methods=["POST"])
def scraperapi_search():
    """
    Run scraperapi_scraper.py with the given API key.
    Expected JSON body:
      {
        "keyword": "anker",             # required
        "api_key": "c8ccc707...",        # required
        "countries": ["us","de","uk"],   # optional
        "date_from": "2026-08-10",       # optional, post-filter
        "date_to": "2026-08-16",         # optional, post-filter
      }
    """
    data = request.get_json(force=True)
    keyword = data.get("keyword", "").strip()
    api_key = data.get("api_key", "").strip()

    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400
    if not api_key:
        return jsonify({"error": "ScraperAPI key is required"}), 400

    countries = data.get("countries", [])
    date_from = data.get("date_from", "")
    date_to = data.get("date_to", "")
    full_mode = data.get("full_mode", False)

    # Fast mode: 20s per request, 120s total subprocess timeout
    # Full mode: 45s per request (JS rendering needs more), 300s total
    per_request_timeout = 45 if full_mode else 20
    subprocess_timeout = 300 if full_mode else 120

    cmd = [sys.executable, str(SCRIPTS_DIR / "scraperapi_scraper.py")]
    cmd += ["-k", keyword, "--api-key", api_key]
    cmd += ["--timeout", str(per_request_timeout)]
    if countries:
        cmd += ["-c", ",".join(countries)]
    if full_mode:
        cmd += ["--full-mode"]

    job_id = str(uuid.uuid4())[:8]
    output_file = RESULTS_DIR / f"scraperapi_{job_id}.json"
    cmd += ["--output", str(output_file)]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=subprocess_timeout,
            cwd=str(SCRIPTS_DIR)
        )

        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                results = json.load(f)
            output_file.unlink(missing_ok=True)
            posts = results.get("posts", [])
            posts = filter_posts_by_date(posts, date_from, date_to)
            return jsonify({
                "ok": True,
                "posts": posts,
                "log": result.stdout[-3000:] if result.stdout else ""
            })
        else:
            # Try to parse from stdout
            stdout = result.stdout or ""
            try:
                # Look for JSON in stdout
                json_start = stdout.find("{")
                if json_start >= 0:
                    results = json.loads(stdout[json_start:])
                    posts = filter_posts_by_date(results.get("posts", []), date_from, date_to)
                    return jsonify({
                        "ok": True,
                        "posts": posts,
                        "log": stdout
                    })
            except json.JSONDecodeError:
                pass

            return jsonify({
                "ok": True,
                "posts": [],
                "log": stdout[-3000:] if stdout else "No output",
                "stderr": result.stderr[-1000:] if result.stderr else ""
            })

    except subprocess.TimeoutExpired:
        mode_label = "Full mode" if full_mode else "Fast mode"
        return jsonify({"error": f"{mode_label} search timed out ({subprocess_timeout}s limit)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "deal-tracker-app"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Deal Brand Tracker app running → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
