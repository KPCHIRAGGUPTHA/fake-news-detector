"""
Domain Trust Checker — Combined Approach
1. Check hardcoded MBFC-curated list (instant)
2. If unknown, check OpenSources public dataset (825 sources, live fetch + cached)
3. Return unified trust result
"""

import requests
import json
import os

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Cache file path ───────────────────────────────────────────────────────────
CACHE_PATH = "backend/domain_cache.json"

# ── Load cache ────────────────────────────────────────────────────────────────
def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_cache(cache: dict):
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except:
        pass

# In-memory cache (loaded once at startup)
_cache = _load_cache()

# ── OpenSources dataset (fetched once, stored in memory) ──────────────────────
_opensources_data = None

def _get_opensources() -> dict:
    global _opensources_data
    if _opensources_data is not None:
        return _opensources_data
    try:
        url  = "https://raw.githubusercontent.com/BigMcLargeHuge/opensources/master/sources/sources.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            _opensources_data = json.loads(resp.text)
            print(f"[DomainChecker] Loaded {len(_opensources_data)} sources from OpenSources dataset")
        else:
            _opensources_data = {}
    except Exception as e:
        print(f"[DomainChecker] Could not load OpenSources dataset: {e}")
        _opensources_data = {}
    return _opensources_data

# ── Hardcoded MBFC-curated list ───────────────────────────────────────────────
RELIABLE_DOMAINS = [
    "reuters.com", "apnews.com", "afp.com", "pti.in", "ians.in",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "telegraph.co.uk", "independent.co.uk", "thetimes.co.uk",
    "ft.com", "wsj.com", "usatoday.com", "latimes.com",
    "chicagotribune.com", "bostonglobe.com", "politico.com",
    "theatlantic.com", "newyorker.com", "time.com",
    "bbc.com", "bbc.co.uk", "cnn.com", "nbcnews.com",
    "abcnews.go.com", "cbsnews.com", "sky.com", "aljazeera.com",
    "france24.com", "dw.com", "rfi.fr", "euronews.com",
    "bloomberg.com", "economist.com", "forbes.com",
    "businessinsider.com", "cnbc.com", "marketwatch.com",
    "nature.com", "sciencemag.org", "nih.gov", "who.int",
    "cdc.gov", "nasa.gov", "un.org", "worldbank.org",
    "npr.org", "pbs.org", "abc.net.au", "cbc.ca",
    "thehindu.com", "ndtv.com", "timesofindia.com",
    "hindustantimes.com", "indianexpress.com", "theprint.in",
    "scroll.in", "thewire.in", "livemint.com",
    "business-standard.com", "deccanherald.com",
    "telegraphindia.com", "tribuneindia.com", "thequint.com",
    "firstpost.com", "outlookindia.com", "caravanmagazine.in",
    "newslaundry.com", "indiatoday.in", "wionews.com",
    "economictimes.indiatimes.com", "financialexpress.com",
    "moneycontrol.com", "pib.gov.in", "rbi.org.in",
    "factcheck.org", "politifact.com", "snopes.com",
    "boomlive.in", "altnews.in", "factly.in",
]

UNRELIABLE_DOMAINS = [
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "worldnewsdailyreport.com", "empirenews.net",
    "nationalreport.net", "yournewswire.com",
    "conservativedailypost.com", "thegatewaypundit.com",
    "thelastlineofdefense.org", "globalresearch.ca",
    "sputniknews.com", "rt.com", "postcard.news",
    "opindia.com", "kreately.in", "tfipost.com",
]

SATIRE_DOMAINS = [
    "theonion.com", "babylonbee.com", "thebeaverton.com",
    "waterfordwhispersnews.com", "newsthump.com",
    "reductress.com", "clickhole.com",
]

MBFC_RATINGS = {
    "reuters.com":        {"bias": "Center",        "factual": "Very High"},
    "apnews.com":         {"bias": "Center",        "factual": "Very High"},
    "bbc.com":            {"bias": "Center-Left",   "factual": "High"},
    "nytimes.com":        {"bias": "Center-Left",   "factual": "High"},
    "wsj.com":            {"bias": "Center-Right",  "factual": "High"},
    "theguardian.com":    {"bias": "Left-Center",   "factual": "High"},
    "bloomberg.com":      {"bias": "Center",        "factual": "High"},
    "thehindu.com":       {"bias": "Center-Left",   "factual": "High"},
    "ndtv.com":           {"bias": "Center",        "factual": "High"},
    "indianexpress.com":  {"bias": "Center",        "factual": "High"},
    "aljazeera.com":      {"bias": "Center-Left",   "factual": "High"},
    "cnn.com":            {"bias": "Left-Center",   "factual": "Mixed"},
    "infowars.com":       {"bias": "Extreme-Right", "factual": "Very Low"},
    "rt.com":             {"bias": "Pro-Russia",    "factual": "Low"},
    "naturalnews.com":    {"bias": "Conspiracy",    "factual": "Very Low"},
    "theprint.in":        {"bias": "Center",        "factual": "High"},
    "scroll.in":          {"bias": "Center-Left",   "factual": "High"},
    "thewire.in":         {"bias": "Left-Center",   "factual": "High"},
    "boomlive.in":        {"bias": "Center",        "factual": "Very High"},
    "altnews.in":         {"bias": "Center-Left",   "factual": "High"},
    "theonion.com":       {"bias": "Satire",        "factual": "N/A"},
}

# OpenSources type → our trust system
OPENSOURCES_TYPE_MAP = {
    "reliable":     ("high",    "✅ Trusted Source",      "Rated reliable by OpenSources dataset"),
    "fake":         ("low",     "🚨 Fake News Site",      "Listed as fake news in OpenSources dataset"),
    "fake news":    ("low",     "🚨 Fake News Site",      "Listed as fake news in OpenSources dataset"),
    "fake ":        ("low",     "🚨 Fake News Site",      "Listed as fake news in OpenSources dataset"),
    "conspiracy":   ("low",     "🚨 Conspiracy Site",     "Listed as conspiracy source in OpenSources dataset"),
    "Conspiracy":   ("low",     "🚨 Conspiracy Site",     "Listed as conspiracy source in OpenSources dataset"),
    "bias":         ("medium",  "⚠️ Biased Source",       "Known for biased reporting (OpenSources dataset)"),
    "political":    ("medium",  "⚠️ Political Bias",      "Strong political bias detected (OpenSources dataset)"),
    "clickbait":    ("medium",  "⚠️ Clickbait Site",      "Known for clickbait content (OpenSources dataset)"),
    "junksci":      ("low",     "🚨 Junk Science",        "Promotes junk/pseudoscience (OpenSources dataset)"),
    "hate":         ("low",     "🚨 Hate Content",        "Associated with hate content (OpenSources dataset)"),
    "rumor":        ("low",     "⚠️ Rumor Site",          "Known for spreading rumors (OpenSources dataset)"),
    "rumor ":       ("low",     "⚠️ Rumor Site",          "Known for spreading rumors (OpenSources dataset)"),
    "satire":       ("satire",  "⚠️ Satire Site",         "Comedy/satire — not real news"),
    "satirical":    ("satire",  "⚠️ Satire Site",         "Comedy/satire — not real news"),
    "state":        ("medium",  "⚠️ State Media",         "State-controlled media outlet"),
    "unreliable":   ("low",     "🚨 Unreliable Source",   "Rated unreliable by OpenSources dataset"),
    "unrealiable":  ("low",     "🚨 Unreliable Source",   "Rated unreliable by OpenSources dataset"),
}


def get_domain(url: str) -> str:
    url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0]


def _build_result(trust, label, description, mbfc=None, source="hardcoded"):
    return {
        "trust":       trust,
        "label":       label,
        "description": description,
        "mbfc":        mbfc,
        "source":      source   # "hardcoded" | "opensources" | "cache" | "unknown"
    }


def check_domain(url: str) -> dict:
    domain = get_domain(url)

    # ── Step 1: Check in-memory cache ─────────────────────────────────────────
    if domain in _cache:
        result = _cache[domain].copy()
        result["source"] = "cache"
        return result

    # ── Step 2: Check hardcoded satire list ───────────────────────────────────
    if any(d in domain for d in SATIRE_DOMAINS):
        result = _build_result(
            "satire", "⚠️ Satire Site",
            "This is a comedy/satire website. Content is not real news.",
            MBFC_RATINGS.get(domain), "hardcoded"
        )
        _cache[domain] = result; _save_cache(_cache)
        return result

    # ── Step 3: Check hardcoded reliable list ─────────────────────────────────
    if any(d in domain for d in RELIABLE_DOMAINS):
        result = _build_result(
            "high", "✅ Trusted Source",
            "Rated reliable — curated from Media Bias Fact Check (MBFC)",
            MBFC_RATINGS.get(domain), "hardcoded"
        )
        _cache[domain] = result; _save_cache(_cache)
        return result

    # ── Step 4: Check hardcoded unreliable list ───────────────────────────────
    if any(d in domain for d in UNRELIABLE_DOMAINS):
        result = _build_result(
            "low", "🚨 Unreliable Source",
            "Known misinformation or low-credibility source (MBFC curated)",
            MBFC_RATINGS.get(domain), "hardcoded"
        )
        _cache[domain] = result; _save_cache(_cache)
        return result

    # ── Step 5: Check OpenSources dataset (825 sources) ───────────────────────
    opensources = _get_opensources()
    # Try exact match and partial match
    matched_key = None
    for key in opensources:
        if domain in key or key in domain:
            matched_key = key
            break

    if matched_key:
        entry      = opensources[matched_key]
        src_type   = entry.get("type", "").strip().lower()
        src_type2  = entry.get("2nd type", "").strip().lower()
        notes      = entry.get("Source Notes (things to know?)", "")

        # Get mapping for primary type, fallback to 2nd type
        mapping = OPENSOURCES_TYPE_MAP.get(src_type) or OPENSOURCES_TYPE_MAP.get(src_type2)

        if mapping:
            trust, label, desc = mapping
            if notes:
                desc += f" — {notes[:120]}"
            result = _build_result(trust, label, desc, None, "opensources")
            _cache[domain] = result; _save_cache(_cache)
            return result

    # ── Step 6: Truly unknown ─────────────────────────────────────────────────
    result = _build_result(
        "unknown", "❓ Unknown Source",
        "Not found in any database. Analyze the content carefully.",
        None, "unknown"
    )
    return result
