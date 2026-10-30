
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from scipy.sparse import hstack

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

from preprocessing import preprocess_text


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_FILE = MODEL_DIR / "sentiment_model.pkl"
TFIDF_FILE = MODEL_DIR / "tfidf_vectorizer.pkl"
ENCODER_FILE = MODEL_DIR / "onehot_encoder.pkl"

CAT_COLUMNS = ["category", "product_type", "gender"]


def make_sentiment_from_rating(rating):
    """Convert product ratings into sentiment labels."""
    rating = float(rating)

    if rating >= 4:
        return "Positive"
    elif rating == 3:
        return "Neutral"
    else:
        return "Negative"


def prepare_dataframe(df):
    """Prepare Amazon review data without modifying the original CSV."""

    df = df.copy()

    # Standardize column names.
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Map actual Amazon dataset columns to the required names.
    rename_map = {
        "review": "review_text",
        "reviewtext": "review_text",
        "text": "review_text",
        "overall": "rating",
        "score": "rating",
        "asin": "product_name",
        "product": "product_name",
        "summary": "review_summary",
        "type": "product_type"
    }

    df.rename(columns=rename_map, inplace=True)

    # Ensure the required review text column exists.
    if "review_text" not in df.columns:
        raise ValueError(
            "Dataset must contain reviewText, review_text, review, or text."
        )

    # Use product ID when product name is unavailable.
    if "product_name" not in df.columns:
        df["product_name"] = "Unknown"

    # Convert ratings to numeric values.
    if "rating" not in df.columns:
        raise ValueError(
            "Dataset must contain an overall or rating column."
        )

    df["rating"] = pd.to_numeric(
        df["rating"], errors="coerce"
    )

    # Remove rows without a valid review or rating.
    df = df.dropna(subset=["review_text", "rating"]).copy()

    df["review_text"] = df["review_text"].astype(str).str.strip()

    df = df[
        (df["review_text"] != "") &
        (df["review_text"].str.lower() != "nan")
    ].copy()

    df["rating"] = df["rating"].clip(1, 5)

    # Fill optional categorical features.
    for col in CAT_COLUMNS:
        if col not in df.columns:
            df[col] = "Unknown"

        df[col] = df[col].fillna("Unknown").astype(str)

    df["product_name"] = (
        df["product_name"].fillna("Unknown").astype(str)
    )

    # Create sentiment labels from ratings.
    if "sentiment" not in df.columns:
        df["sentiment"] = df["rating"].apply(
            make_sentiment_from_rating
        )
    else:
        df["sentiment"] = (
            df["sentiment"].astype(str).str.strip().str.title()
        )

        valid_labels = {"Positive", "Neutral", "Negative"}

        invalid = ~df["sentiment"].isin(valid_labels)

        df.loc[invalid, "sentiment"] = df.loc[
            invalid, "rating"
        ].apply(make_sentiment_from_rating)

    df.reset_index(drop=True, inplace=True)

    if len(df) < 6:
        raise ValueError(
            "At least 6 valid customer reviews are required."
        )

    if df["sentiment"].nunique() < 2:
        raise ValueError(
            "At least two sentiment classes are required for training."
        )

    return df


def train_model(csv_path):
    """Train Logistic Regression using TF-IDF and categorical features."""

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {csv_path}"
        )

    print("Loading dataset...")

    df = prepare_dataframe(pd.read_csv(csv_path))

    print("Valid reviews:", len(df))
    print("Sentiment distribution:")
    print(df["sentiment"].value_counts())

    # Preprocess review text.
    df["clean_review"] = df["review_text"].apply(
        preprocess_text
    )

    # Extract text features.
    vectorizer = TfidfVectorizer(
        max_features=1000,
        ngram_range=(1, 2)
    )

    X_text = vectorizer.fit_transform(df["clean_review"])

    # Encode categorical features.
    encoder = OneHotEncoder(handle_unknown="ignore")

    X_category = encoder.fit_transform(df[CAT_COLUMNS])

    # Combine text and categorical features.
    X = hstack([X_text, X_category]).tocsr()
    y = df["sentiment"]

    # Use stratification only when each class has enough examples.
    class_counts = y.value_counts()

    stratify_labels = (
        y
        if len(class_counts) >= 2 and class_counts.min() >= 2
        else None
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify_labels
    )

    # Train the classification model.
    model = LogisticRegression(max_iter=1000)

    model.fit(X_train, y_train)

    # Evaluate using held-out test data.
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": round(
            accuracy_score(y_test, y_pred), 3
        ),
        "precision": round(
            precision_score(
                y_test, y_pred,
                average="weighted",
                zero_division=0
            ), 3
        ),
        "recall": round(
            recall_score(
                y_test, y_pred,
                average="weighted",
                zero_division=0
            ), 3
        ),
        "f1": round(
            f1_score(
                y_test, y_pred,
                average="weighted",
                zero_division=0
            ), 3
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            y_pred,
            labels=["Positive", "Neutral", "Negative"]
        ).tolist()
    }

    # Save trained model components.
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, TFIDF_FILE)
    joblib.dump(encoder, ENCODER_FILE)

    # Calculate the most frequent TF-IDF terms.
    mean_scores = np.asarray(
        X_text.mean(axis=0)
    ).ravel()

    terms = np.array(
        vectorizer.get_feature_names_out()
    )

    top_indices = mean_scores.argsort()[::-1][:15]

    top_words = [
        {
            "word": str(terms[i]),
            "score": round(float(mean_scores[i]), 4)
        }
        for i in top_indices
    ]

    model_info = {
        "metrics": metrics,
        "top_words": top_words
    }

    print("Model training completed.")
    print("Evaluation metrics:", json.dumps(metrics, indent=2))

    return df, model_info


def predict_sentiment(
    review,
    category="Unknown",
    product_type="Unknown",
    gender="Unknown"
):
    """Predict the sentiment of a new customer review."""

    if not MODEL_FILE.exists():
        raise ValueError(
            "Model not trained yet. Start the app and train the dataset first."
        )

    model = joblib.load(MODEL_FILE)
    vectorizer = joblib.load(TFIDF_FILE)
    encoder = joblib.load(ENCODER_FILE)

    clean_review = preprocess_text(review)

    X_text = vectorizer.transform([clean_review])

    category_df = pd.DataFrame([{
        "category": category,
        "product_type": product_type,
        "gender": gender
    }])

    X_category = encoder.transform(category_df[CAT_COLUMNS])

    X = hstack([X_text, X_category]).tocsr()

    return str(model.predict(X)[0])
