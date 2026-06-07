import joblib
import re
import string
import math
import nltk

nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))

model      = joblib.load("models/model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")

# ── Word Lists ────────────────────────────────────────────────────────────────
CLICKBAIT_WORDS = [
    "shocking", "unbelievable", "mind-blowing", "you won't believe",
    "breaking", "exclusive", "bombshell", "exposed", "leaked",
    "urgent", "alert", "must see", "viral", "outrage", "sensational",
    "jaw-dropping", "stunning", "explosive", "scandalous", "incredible"
]

CONSPIRACY_WORDS = [
    "deep state", "new world order", "they don't want you to know",
    "mainstream media won't tell", "cover-up", "conspiracy", "hoax",
    "plandemic", "false flag", "illuminati", "chemtrails", "microchip",
    "globalist", "shadow government", "secret agenda", "they are hiding",
    "suppressed", "banned from tv", "what they won't tell you"
]

EMOTIONAL_WORDS = [
    "destroy", "evil", "corrupt", "disgusting", "traitor", "criminal",
    "worst ever", "hate", "rage", "furious", "terrifying", "catastrophic",
    "disastrous", "horrifying", "outrageous", "despicable", "vile",
    "wicked", "atrocious", "abomination", "shameful", "pathetic"
]

EXAGGERATION_WORDS = [
    "always", "never", "everyone", "nobody", "none",
    "completely", "totally", "absolutely", "perfect",
    "best ever", "greatest", "biggest ever", "most dangerous",
    "worst in history", "unprecedented", "100%", "guaranteed"
]

UNRELIABLE_PATTERNS = [
    r'\b(they|government|elite|globalist)s?\s+(are\s+)?(hiding|suppressing|covering up)',
    r'wake\s*up\s*(people|america|sheeple)',
    r'share\s+before\s+(this\s+is\s+)?(deleted|removed|banned)',
    r'what\s+(they|media)\s+(won\'t|don\'t|refuses?\s+to)\s+tell',
    r'(doctors|scientists|experts)\s+(hate|don\'t want you)',
    r'this\s+will\s+be\s+(deleted|removed|censored)',
]

RELIABLE_INDICATORS = [
    "according to", "reported by", "sources say", "officials said",
    "study shows", "research indicates", "data shows", "percent",
    "announced", "confirmed", "spokesperson", "statement released",
    "press conference", "official report", "survey found",
    "analysis shows", "experts say", "cited", "published in"
]

FORMAL_LANGUAGE = [
    "government", "parliament", "minister", "official", "policy",
    "legislation", "amendment", "treaty", "bilateral", "diplomatic",
    "authority", "committee", "commission", "department", "bureau",
    "agency", "institution", "organization", "administration"
]

QUESTION_HEADLINE_WORDS = [
    "really", "actually", "secret", "true", "truth",
    "hidden", "exposed", "revealed", "finally"
]


def clean_text(text: str) -> str:
    t = text.lower()
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'https?://\S+|www\.\S+', '', t)
    t = re.sub(r'<.*?>+', '', t)
    t = re.sub(r'[%s]' % re.escape(string.punctuation), '', t)
    t = re.sub(r'\n', ' ', t)
    t = re.sub(r'\w*\d\w*', '', t)
    tokens = t.split()
    tokens = [w for w in tokens if w not in STOP_WORDS]
    return " ".join(tokens)


def find_suspicious_words(text: str) -> list:
    found = []
    lower = text.lower()
    for w in CLICKBAIT_WORDS + EMOTIONAL_WORDS + EXAGGERATION_WORDS:
        if w in lower and w not in found:
            found.append(w)
    for pattern in UNRELIABLE_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            found.append(match.group(0).strip())
    return found


# ── Credibility Scoring ───────────────────────────────────────────────────────

def score_language_tone(text: str, lower: str, words: list) -> dict:
    """
    Measures how neutral vs sensational the language is.
    High score = neutral/formal. Low score = emotional/clickbait.
    """
    deductions = 0
    flags      = []

    cb_hits = [w for w in CLICKBAIT_WORDS if w in lower]
    if cb_hits:
        deductions += min(len(cb_hits) * 15, 40)
        flags.append(f"Clickbait words: {', '.join(cb_hits[:3])}")

    em_hits = [w for w in EMOTIONAL_WORDS if w in lower]
    if em_hits:
        deductions += min(len(em_hits) * 12, 35)
        flags.append(f"Emotional language: {', '.join(em_hits[:3])}")

    excl = text.count("!")
    if excl >= 3:
        deductions += 20
        flags.append(f"Excessive exclamation marks ({excl}x)")
    elif excl >= 1:
        deductions += excl * 5

    formal_hits = [w for w in FORMAL_LANGUAGE if w in lower]
    bonus = min(len(formal_hits) * 5, 20)

    rel_hits = [w for w in RELIABLE_INDICATORS if w in lower]
    bonus += min(len(rel_hits) * 8, 25)

    raw   = max(0, 100 - deductions + bonus)
    score = min(100, raw)
    return {"score": score, "flags": flags,
            "label": "Language Tone",
            "description": "Measures neutrality vs sensationalism in writing style"}


def score_emotional_manipulation(text: str, lower: str, words: list) -> dict:
    """
    Detects emotional manipulation techniques.
    High score = low manipulation. Low score = high manipulation.
    """
    deductions = 0
    flags      = []

    con_hits = [w for w in CONSPIRACY_WORDS if w in lower]
    if con_hits:
        deductions += min(len(con_hits) * 20, 50)
        flags.append(f"Conspiracy language: {', '.join(con_hits[:2])}")

    for pattern in UNRELIABLE_PATTERNS:
        if re.search(pattern, lower):
            deductions += 25
            flags.append("Hidden-truth narrative pattern")
            break

    cap_words = [w for w in words if w.isupper() and len(w) > 3]
    if len(cap_words) >= 3:
        deductions += 20
        flags.append(f"ALL CAPS words: {' '.join(cap_words[:3])}")
    elif len(cap_words) >= 1:
        deductions += len(cap_words) * 5

    ex_hits = [w for w in EXAGGERATION_WORDS if w in lower]
    if ex_hits:
        deductions += min(len(ex_hits) * 8, 25)
        flags.append(f"Exaggerated claims: {', '.join(ex_hits[:3])}")

    score = max(0, 100 - deductions)
    return {"score": score, "flags": flags,
            "label": "Emotional Manipulation",
            "description": "Detects fear, outrage, and psychological pressure tactics"}


def score_structural_quality(text: str, lower: str, words: list) -> dict:
    """
    Measures article structure quality — length, balance, sourcing.
    """
    deductions = 0
    bonus      = 0
    flags      = []

    word_count = len(words)
    if word_count < 20:
        deductions += 40
        flags.append(f"Very short text ({word_count} words) — insufficient context")
    elif word_count < 50:
        deductions += 20
        flags.append(f"Short text ({word_count} words) — limited context")
    elif word_count > 200:
        bonus += 15

    rel_hits = [w for w in RELIABLE_INDICATORS if w in lower]
    if rel_hits:
        bonus += min(len(rel_hits) * 10, 30)
    else:
        deductions += 15
        flags.append("No source attribution found")

    if text.strip().endswith("?"):
        q_hits = [w for w in QUESTION_HEADLINE_WORDS if w in lower]
        if q_hits:
            deductions += 20
            flags.append("Question headline implying unverified claims")

    has_numbers = bool(re.search(r'\b\d+\.?\d*\s*(%|percent|million|billion|thousand)\b', lower))
    if has_numbers:
        bonus += 10

    score = max(0, min(100, 70 + bonus - deductions))
    return {"score": score, "flags": flags,
            "label": "Structural Quality",
            "description": "Evaluates article length, sourcing, and factual structure"}


def score_headline_integrity(text: str, lower: str, words: list) -> dict:
    """
    Checks headline vs content consistency and headline quality.
    """
    deductions = 0
    flags      = []

    first_line = text.split('.')[0] if '.' in text else text[:100]
    first_lower = first_line.lower()

    cb_in_headline = [w for w in CLICKBAIT_WORDS if w in first_lower]
    if cb_in_headline:
        deductions += min(len(cb_in_headline) * 20, 45)
        flags.append(f"Clickbait in headline: {', '.join(cb_in_headline[:2])}")

    caps_in_headline = len([w for w in first_line.split() if w.isupper() and len(w) > 2])
    if caps_in_headline >= 2:
        deductions += 20
        flags.append("ALL CAPS in headline")

    excl_in_headline = first_line.count("!")
    if excl_in_headline >= 2:
        deductions += 15
        flags.append(f"Multiple exclamation marks in headline")

    if first_lower.strip().endswith("?"):
        deductions += 10
        flags.append("Question-format headline")

    score = max(0, 100 - deductions)
    return {"score": score, "flags": flags,
            "label": "Headline Integrity",
            "description": "Checks for misleading or sensational headline patterns"}


def score_source_credibility(text: str, lower: str, words: list, domain_trust: dict = None) -> dict:
    """
    Combines domain trust with in-text source attribution.
    """
    base  = 50  # neutral starting point
    flags = []

    # Domain trust from Phase 2
    if domain_trust:
        trust_level = domain_trust.get("trust", "unknown")
        if trust_level == "high":
            base = 90
        elif trust_level == "low":
            base = 10
            flags.append(f"Domain flagged as unreliable: {domain_trust.get('label','')}")
        elif trust_level == "satire":
            base = 20
            flags.append("Satire website — not a news source")
        else:
            base = 50

    # In-text signals
    rel_hits = [w for w in RELIABLE_INDICATORS if w in lower]
    bonus    = min(len(rel_hits) * 8, 25)

    known_outlets = [
        "reuters", "ap news", "associated press", "bbc", "ndtv",
        "the hindu", "indian express", "times of india", "bloomberg"
    ]
    outlet_hits = [o for o in known_outlets if o in lower]
    if outlet_hits:
        bonus += min(len(outlet_hits) * 10, 20)

    score = min(100, max(0, base + bonus))
    if not flags and score < 50:
        flags.append("Low source credibility signals")
    return {"score": score, "flags": flags,
            "label": "Source Credibility",
            "description": "Combines domain reputation with in-text source attribution"}


def compute_credibility_scores(text: str, ml_confidence: float,
                                ml_label: str, domain_trust: dict = None) -> dict:
    lower = text.lower()
    words = text.split()

    tone       = score_language_tone(text, lower, words)
    emotion    = score_emotional_manipulation(text, lower, words)
    structure  = score_structural_quality(text, lower, words)
    headline   = score_headline_integrity(text, lower, words)
    source     = score_source_credibility(text, lower, words, domain_trust)

    # ML model score — convert confidence to a 0-100 credibility score
    ml_score = ml_confidence if ml_label == "Real" else (100 - ml_confidence)
    ml_factor = {
        "score":       round(ml_score, 1),
        "flags":       [],
        "label":       "ML Model Score",
        "description": "TF-IDF + Logistic Regression trained on 44,898 news articles"
    }

    # Weighted overall score
    # ML gets highest weight, then source, then others
    weights = {
        "ml":        0.35,
        "source":    0.20,
        "tone":      0.15,
        "emotion":   0.15,
        "structure": 0.10,
        "headline":  0.05,
    }

    overall = (
        ml_factor["score"]  * weights["ml"]        +
        source["score"]     * weights["source"]     +
        tone["score"]       * weights["tone"]       +
        emotion["score"]    * weights["emotion"]    +
        structure["score"]  * weights["structure"]  +
        headline["score"]   * weights["headline"]
    )
    overall = round(overall, 1)

    # Verdict based on overall score
    if overall >= 70:
        verdict = "Likely Credible"
        verdict_color = "real"
    elif overall >= 45:
        verdict = "Questionable"
        verdict_color = "warn"
    else:
        verdict = "Likely Misinformation"
        verdict_color = "fake"

    return {
        "overall":       overall,
        "verdict":       verdict,
        "verdict_color": verdict_color,
        "factors": [
            ml_factor,
            source,
            tone,
            emotion,
            structure,
            headline,
        ]
    }


def analyze_reasons(text: str, label: str) -> list:
    reasons = []
    lower   = text.lower()
    words   = text.split()

    cb_hits = [w for w in CLICKBAIT_WORDS if w in lower]
    if cb_hits:
        reasons.append(f"Clickbait language detected: {', '.join(cb_hits[:3])}")

    con_hits = [w for w in CONSPIRACY_WORDS if w in lower]
    if con_hits:
        reasons.append(f"Conspiracy language detected: {', '.join(con_hits[:2])}")

    em_hits = [w for w in EMOTIONAL_WORDS if w in lower]
    if em_hits:
        reasons.append(f"Emotionally charged words: {', '.join(em_hits[:3])}")

    ex_hits = [w for w in EXAGGERATION_WORDS if w in lower]
    if ex_hits:
        reasons.append(f"Absolute/exaggerated language: {', '.join(ex_hits[:3])}")

    cap_words = [w for w in words if w.isupper() and len(w) > 3]
    if len(cap_words) >= 2:
        reasons.append(f"Excessive capitalization: {' '.join(cap_words[:4])}")

    excl = text.count("!")
    if excl >= 2:
        reasons.append(f"Multiple exclamation marks ({excl}x) — sensational tone")

    if text.strip().endswith("?") and len(words) < 15:
        reasons.append("Question-format headline — often used to imply unverified claims")

    for pattern in UNRELIABLE_PATTERNS:
        if re.search(pattern, lower):
            reasons.append("Pattern suggests hidden-truth narrative")
            break

    rel_hits = [w for w in RELIABLE_INDICATORS if w in lower]
    if rel_hits and label == "Real":
        reasons.append(f"Credible language patterns: {', '.join(rel_hits[:3])}")

    if len(words) < 15:
        reasons.append("Short text — limited context, lower confidence")

    if label == "Real" and not reasons:
        reasons.append("Neutral reporting tone with no red flags")

    return reasons if reasons else ["No specific red flags detected"]


def predict(text: str, domain_trust: dict = None) -> dict:
    cleaned    = clean_text(text)
    vec        = vectorizer.transform([cleaned])
    pred       = model.predict(vec)[0]
    proba      = model.predict_proba(vec)[0]

    label      = "Real" if pred == 1 else "Fake"
    confidence = round(float(max(proba)) * 100, 2)
    reasons    = analyze_reasons(text, label)
    highlights = find_suspicious_words(text)
    credibility = compute_credibility_scores(text, confidence, label, domain_trust)

    return {
        "label":       label,
        "confidence":  confidence,
        "reasons":     reasons,
        "highlights":  highlights,
        "credibility": credibility
    }