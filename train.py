import pandas as pd
import numpy as np
import re
import string
import joblib
import os
import nltk

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# Download NLTK data
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))

# ── 1. Load Data ──────────────────────────────────────────────────────────────
print("Loading data...")
true_df = pd.read_csv("data/True.csv")
fake_df = pd.read_csv("data/Fake.csv")

true_df["label"] = 1   # Real = 1
fake_df["label"] = 0   # Fake = 0

df = pd.concat([true_df, fake_df], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle

# Combine title + text for better accuracy
df["content"] = df["title"].fillna("") + " " + df["text"].fillna("")

print(f"Total samples: {len(df)} | Real: {df['label'].sum()} | Fake: {(df['label']==0).sum()}")

# ── 2. Text Cleaning ──────────────────────────────────────────────────────────
def clean_text(text):
    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)           # Remove brackets
    text = re.sub(r'https?://\S+|www\.\S+', '', text)  # Remove URLs
    text = re.sub(r'<.*?>+', '', text)            # Remove HTML tags
    text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)  # Remove punctuation
    text = re.sub(r'\n', ' ', text)               # Remove newlines
    text = re.sub(r'\w*\d\w*', '', text)          # Remove words with numbers
    tokens = text.split()
    tokens = [w for w in tokens if w not in STOP_WORDS]
    return " ".join(tokens)

print("Cleaning text...")
df["clean_content"] = df["content"].apply(clean_text)

# ── 3. Train/Test Split ───────────────────────────────────────────────────────
X = df["clean_content"]
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ── 4. TF-IDF Vectorization ───────────────────────────────────────────────────
print("Vectorizing...")
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec  = vectorizer.transform(X_test)

# ── 5. Train Model ────────────────────────────────────────────────────────────
print("Training model...")
model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

# ── 6. Evaluate ───────────────────────────────────────────────────────────────
y_pred = model.predict(X_test_vec)
acc = accuracy_score(y_test, y_pred)
print(f"\n✅ Accuracy: {acc * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Fake", "Real"]))

# ── 7. Save Model & Vectorizer ────────────────────────────────────────────────
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/model.pkl")
joblib.dump(vectorizer, "models/vectorizer.pkl")
print("\n✅ Model saved to models/model.pkl")
print("✅ Vectorizer saved to models/vectorizer.pkl")
print("\nTraining complete! You can now run the backend.")
