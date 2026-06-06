import joblib
import re
import string
import nltk

nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))

model      = joblib.load("models/model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")

# ── Indicator word lists ───────────────────────────────────────────────────────
CLICKBAIT_WORDS = [
    "shocking", "unbelievable", "mind-blowing", "you won't believe",
    "breaking", "exclusive", "bombshell", "exposed", "leaked",
    "urgent", "alert", "must see", "viral", "outrage"
]

CONSPIRACY_WORDS = [
    "deep state", "new world order", "they don't want you to know",
    "mainstream media won't tell", "cover-up", "conspiracy", "hoax",
    "plandemic", "false flag", "illuminati", "chemtrails", "microchip"
]

EMOTIONAL_WORDS = [
    "destroy", "evil", "corrupt", "disgusting", "traitor", "criminal",
    "worst ever", "greatest ever", "hate", "rage", "furious",
    "terrifying", "catastrophic", "disastrous", "horrifying"
]

EXAGGERATION_WORDS = [
    "always", "never", "everyone", "nobody", "all", "none",
    "completely", "totally", "absolutely", "perfect", "worst",
    "best ever", "greatest", "biggest ever", "most dangerous"
]

UNRELIABLE_PATTERNS = [
    r'\b(they|government|elite|globalist)s?\s+(are\s+)?(hiding|suppressing|covering up)',
    r'wake\s*up\s*(people|america|sheeple)',
    r'share\s+before\s+(this\s+is\s+)?(deleted|removed|banned)',
    r'what\s+(they|media)\s+(won\'t|don\'t|refuses?\s+to)\s+tell',
]

RELIABLE_INDICATORS = [
    "according to", "reported by", "sources say", "officials said",
    "study shows", "research indicates", "data shows", "percent",
    "announced", "confirmed", "spokesperson", "statement"
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
    """Return list of suspicious words found in the original text."""
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


def analyze_reasons(text: str, label: str) -> list:
    reasons = []
    lower   = text.lower()
    words   = text.split()

    # Clickbait
    cb_hits = [w for w in CLICKBAIT_WORDS if w in lower]
    if cb_hits:
        reasons.append(f"Clickbait language detected: {', '.join(cb_hits[:3])}")

    # Conspiracy
    con_hits = [w for w in CONSPIRACY_WORDS if w in lower]
    if con_hits:
        reasons.append(f"Conspiracy language detected: {', '.join(con_hits[:2])}")

    # Emotional manipulation
    em_hits = [w for w in EMOTIONAL_WORDS if w in lower]
    if em_hits:
        reasons.append(f"Emotionally charged words: {', '.join(em_hits[:3])}")

    # Exaggeration
    ex_hits = [w for w in EXAGGERATION_WORDS if w in lower]
    if ex_hits:
        reasons.append(f"Absolute/exaggerated language: {', '.join(ex_hits[:3])}")

    # ALL CAPS check
    cap_words = [w for w in words if w.isupper() and len(w) > 3]
    if len(cap_words) >= 2:
        reasons.append(f"Excessive capitalization: {' '.join(cap_words[:4])}")

    # Exclamation marks
    excl = text.count("!")
    if excl >= 2:
        reasons.append(f"Multiple exclamation marks ({excl}x) — sensational tone")

    # Question mark headline
    if text.strip().endswith("?") and len(words) < 15:
        reasons.append("Question-format headline — often used to imply unverified claims")

    # Unreliable patterns
    for pattern in UNRELIABLE_PATTERNS:
        if re.search(pattern, lower):
            reasons.append("Pattern suggests hidden-truth narrative")
            break

    # Reliable indicators (positive signals)
    rel_hits = [w for w in RELIABLE_INDICATORS if w in lower]
    if rel_hits and label == "Real":
        reasons.append(f"Credible language patterns: {', '.join(rel_hits[:3])}")

    # Short text
    if len(words) < 15:
        reasons.append("Short text — limited context, lower confidence")

    # Passive / neutral reporting
    if label == "Real" and not reasons:
        reasons.append("Neutral reporting tone with no red flags")

    return reasons if reasons else ["No specific red flags detected"]


def predict(text: str) -> dict:
    cleaned    = clean_text(text)
    vec        = vectorizer.transform([cleaned])
    pred       = model.predict(vec)[0]
    proba      = model.predict_proba(vec)[0]

    label      = "Real" if pred == 1 else "Fake"
    confidence = round(float(max(proba)) * 100, 2)
    reasons    = analyze_reasons(text, label)
    highlights = find_suspicious_words(text)

    return {
        "label":      label,
        "confidence": confidence,
        "reasons":    reasons,
        "highlights": highlights   # words to highlight in frontend
    }