import re
import pandas as pd


GENERIC_KEYWORDS = [
    "running shoes",
    "sports shoes",
    "casual shoes",
    "bluetooth speaker",
    "washing machine",
    "microwave oven",
    "mixer grinder",
    "electric trimmer",
    "power bank",
    "smart watch",
    "smart tv",
    "headphones",
    "earbuds",
    "laptop",
    "shoes",
    "phone",
    "mobile",
    "smartphone",
    "shirt",
    "t-shirt",
    "jeans",
    "jacket",
    "watch",
    "camera",
    "bag",
    "backpack",
    "television",
    "tv",
    "refrigerator",
    "trimmer"
]

STOP_WORDS = {
    "i", "want", "to", "buy", "a", "an", "the",
    "need", "looking", "for", "good", "best",
    "product", "please", "give", "me", "show",
    "recommend", "can"
}


def extract_product_keyword(query, df=None):
    """
    Extract a product or category keyword from the user's sentence.
    """
    query_clean = query.strip().lower()

    # Check known generic product types/categories first (longer phrases first)
    sorted_generics = sorted(GENERIC_KEYWORDS, key=len, reverse=True)
    for kw in sorted_generics:
        if kw in query_clean:
            return kw

    # If df is provided, check if any product name from df is in the query
    if df is not None and not df.empty and "product_name" in df.columns:
        for p_name in sorted(df["product_name"].dropna().unique(), key=len, reverse=True):
            if str(p_name).lower() in query_clean:
                return str(p_name).lower()

    # If no predefined keyword is found, remove common stop words
    words = re.findall(r"[a-zA-Z0-9]+", query_clean)
    keywords = [word for word in words if word not in STOP_WORDS]

    if keywords:
        return " ".join(keywords)

    return None


def select_recommended_product(products, user_query):
    """
    Select the intended product for the recommendation card.
    If the user specifically requested a product (e.g. 'Budget Laptop'),
    select that product instead of always defaulting to the highest-scoring one.
    If the search is generic (e.g. 'laptop'), default to the top-scoring product.
    """
    if not products:
        return None

    query_lower = user_query.strip().lower()
    raw_query_tokens = re.findall(r"[a-z0-9]+", query_lower)
    raw_query_str = " ".join(raw_query_tokens)

    # 1. Exact match with product_name (case-insensitive & token-normalized)
    for p in products:
        p_name = p["product_name"].lower()
        p_tokens = re.findall(r"[a-z0-9]+", p_name)
        if p_name == query_lower or " ".join(p_tokens) == raw_query_str:
            return p

    # 2. Check if complete product_name appears as a normalized word-sequence in user_query
    for p in sorted(products, key=lambda x: len(x["product_name"]), reverse=True):
        p_tokens = re.findall(r"[a-z0-9]+", p["product_name"].lower())
        p_str = " ".join(p_tokens)
        if p_str and (p_str in raw_query_str or p["product_name"].lower() in query_lower):
            return p

    # 3. Clean query tokens (remove conversational stop words)
    query_tokens = [w for w in raw_query_tokens if w not in STOP_WORDS]
    clean_query_str = " ".join(query_tokens)

    # Distinguish distinctive model/brand tokens from generic category terms
    distinctive_tokens = [w for w in query_tokens if w not in GENERIC_KEYWORDS]

    # If the query contains ONLY generic category words (e.g. "laptop", "shoes", "running shoes"),
    # do not match by substring; return the highest-scoring product.
    if not distinctive_tokens:
        return products[0]

    # 4. Check if clean query is a normalized word-sequence in product_name
    for p in products:
        p_tokens = re.findall(r"[a-z0-9]+", p["product_name"].lower())
        p_str = " ".join(p_tokens)
        if clean_query_str and clean_query_str in p_str:
            return p

    # 5. Check for distinctive token overlap (e.g. "budget", "macbook", "inspiron", "air")
    best_p = None
    best_overlap = 0
    for p in products:
        p_tokens = set(re.findall(r"[a-z0-9]+", p["product_name"].lower()))
        overlap = sum(1 for t in distinctive_tokens if t in p_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_p = p

    if best_p and best_overlap > 0:
        return best_p

    # 6. Default to the highest-scoring product
    return products[0]


# Backwards compatibility alias
select_target_product = select_recommended_product


def get_recommendation(df, user_query):

    product_keyword = extract_product_keyword(user_query, df)

    if not product_keyword:
        return {
            "found": False,
            "message": "Sorry, I could not identify the product."
        }

    # Search product name, category and product type
    keyword = product_keyword.lower()

    mask = (
        df["product_name"].str.lower().str.contains(keyword, na=False)
        | df["category"].str.lower().str.contains(keyword, na=False)
        | df["product_type"].str.lower().str.contains(keyword, na=False)
    )

    matched_df = df[mask].copy()

    # If matched_df is empty, try matching individual distinctive words
    if matched_df.empty:
        words = [w for w in re.findall(r"[a-zA-Z0-9]+", keyword) if w not in STOP_WORDS]
        for w in words:
            word_mask = (
                df["product_name"].str.lower().str.contains(w, na=False)
                | df["category"].str.lower().str.contains(w, na=False)
                | df["product_type"].str.lower().str.contains(w, na=False)
            )
            if word_mask.any():
                matched_df = df[word_mask].copy()
                break

    if matched_df.empty:
        return {
            "found": False,
            "product": product_keyword,
            "message": f"No products found for '{product_keyword}'."
        }

    # If matched_df matched only 1 specific product (e.g. Apple MacBook Air),
    # expand to include other products of the same product_type for comparative analysis table
    matched_types = matched_df["product_type"].dropna().unique()
    if len(matched_df["product_name"].unique()) == 1 and len(matched_types) == 1:
        expanded_mask = df["product_type"].str.lower() == str(matched_types[0]).lower()
        if expanded_mask.any():
            matched_df = df[expanded_mask].copy()

    # Create sentiment if it does not already exist
    if "sentiment" not in matched_df.columns:
        matched_df["sentiment"] = matched_df["rating"].apply(
            lambda x: "Positive" if x >= 4
            else "Neutral" if x == 3
            else "Negative"
        )

    products = []

    # Analyze each individual product
    for product_name, product_df in matched_df.groupby("product_name"):

        total = len(product_df)

        positive = (
            product_df["sentiment"] == "Positive"
        ).sum()

        neutral = (
            product_df["sentiment"] == "Neutral"
        ).sum()

        negative = (
            product_df["sentiment"] == "Negative"
        ).sum()

        average_rating = product_df["rating"].mean()

        positive_percent = (positive / total) * 100
        neutral_percent = (neutral / total) * 100
        negative_percent = (negative / total) * 100

        # Recommendation score
        score = (
            (average_rating / 5) * 50
            + (positive_percent / 100) * 50
        )

        score = round(score, 2)

        # Recommendation decision
        if average_rating >= 4 and positive_percent >= 60:
            recommendation = "BUY"
            recommendation_text = "✓ YES, YOU CAN BUY THIS PRODUCT"

        elif average_rating >= 3 and positive_percent >= 40:
            recommendation = "CONSIDER"
            recommendation_text = "⚠ CONSIDER THIS PRODUCT"

        else:
            recommendation = "AVOID"
            recommendation_text = "✗ NO, THIS PRODUCT IS NOT RECOMMENDED"

        products.append({
            "product_name": product_name,
            "average_rating": round(average_rating, 2),
            "positive_percent": round(positive_percent, 1),
            "neutral_percent": round(neutral_percent, 1),
            "negative_percent": round(negative_percent, 1),
            "score": score,
            "recommendation": recommendation,
            "recommendation_text": recommendation_text,
            "review_count": total
        })

    # Sort best products first
    products.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Select the target product matching user's query
    best_product = select_recommended_product(products, user_query)

    return {
        "found": True,
        "product": product_keyword,
        "best_product": best_product,
        "products": products
    }