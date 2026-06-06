import joblib
import re
import string
import nltk

nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))

model      = joblib.load("models/model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'<.*?>+', '', text)
    text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\w*\d\w*', '', text)
    tokens = text.split()
    tokens = [w for w in tokens if w not in STOP_WORDS]
    return " ".join(tokens)


def predict(text: str) -> dict:
    cleaned = clean_text(text)
    vec     = vectorizer.transform([cleaned])
    pred    = model.predict(vec)[0]
    proba   = model.predict_proba(vec)[0]

    label      = "Real" if pred == 1 else "Fake"
    confidence = round(float(max(proba)) * 100, 2)

    # Simple reason tags
    reasons = []
    lower = text.lower()
    if any(w in lower for w in ["!", "breaking", "shocking", "exclusive", "you won't believe"]):
        reasons.append("Sensational / clickbait language detected")
    if any(w in lower for w in ["secret", "they don't want you to know", "cover-up", "conspiracy"]):
        reasons.append("Conspiracy-related language detected")
    if len(text.split()) < 20:
        reasons.append("Very short text — limited context for analysis")
    if text == text.upper() and len(text) > 10:
        reasons.append("ALL CAPS detected — common in misleading headlines")

    return {
        "label":      label,
        "confidence": confidence,
        "reasons":    reasons if reasons else ["No specific red flags detected"]
    }
