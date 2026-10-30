import sys
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------------------------
# Ensure utf-8 encoding on standard output for terminal compatibility
# ------------------------------------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ------------------------------------------------------------------------------
# Define PROJECT_DIR reliably using the test file's location
# ------------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Import actual recommendation functions from the project
from recommendation import select_recommended_product, get_recommendation

# ------------------------------------------------------------------------------
# Mock Product Datasets for Unit Testing
# ------------------------------------------------------------------------------
mock_laptops = [
    {
        "product_name": "Apple MacBook Air",
        "average_rating": 4.8,
        "positive_percent": 100.0,
        "neutral_percent": 0.0,
        "negative_percent": 0.0,
        "score": 98.0,
        "recommendation": "BUY",
        "recommendation_text": "YES, YOU CAN BUY THIS PRODUCT",
        "review_count": 5
    },
    {
        "product_name": "HP Pavilion Laptop",
        "average_rating": 4.6,
        "positive_percent": 100.0,
        "neutral_percent": 0.0,
        "negative_percent": 0.0,
        "score": 96.0,
        "recommendation": "BUY",
        "recommendation_text": "YES, YOU CAN BUY THIS PRODUCT",
        "review_count": 5
    },
    {
        "product_name": "Lenovo IdeaPad Laptop",
        "average_rating": 4.0,
        "positive_percent": 80.0,
        "neutral_percent": 20.0,
        "negative_percent": 0.0,
        "score": 80.0,
        "recommendation": "BUY",
        "recommendation_text": "YES, YOU CAN BUY THIS PRODUCT",
        "review_count": 5
    },
    {
        "product_name": "Dell Inspiron Laptop",
        "average_rating": 3.0,
        "positive_percent": 20.0,
        "neutral_percent": 60.0,
        "negative_percent": 20.0,
        "score": 40.0,
        "recommendation": "AVOID",
        "recommendation_text": "NO, THIS PRODUCT IS NOT RECOMMENDED",
        "review_count": 5
    },
    {
        "product_name": "Budget Laptop",
        "average_rating": 1.6,
        "positive_percent": 0.0,
        "neutral_percent": 0.0,
        "negative_percent": 100.0,
        "score": 16.0,
        "recommendation": "AVOID",
        "recommendation_text": "NO, THIS PRODUCT IS NOT RECOMMENDED",
        "review_count": 5
    }
]

mock_shoes = [
    {
        "product_name": "Nike Running Shoes",
        "average_rating": 4.6,
        "positive_percent": 100.0,
        "neutral_percent": 0.0,
        "negative_percent": 0.0,
        "score": 96.0,
        "recommendation": "BUY",
        "recommendation_text": "YES, YOU CAN BUY THIS PRODUCT",
        "review_count": 5
    },
    {
        "product_name": "Puma Running Shoes",
        "average_rating": 4.2,
        "positive_percent": 80.0,
        "neutral_percent": 0.0,
        "negative_percent": 20.0,
        "score": 82.0,
        "recommendation": "BUY",
        "recommendation_text": "YES, YOU CAN BUY THIS PRODUCT",
        "review_count": 5
    },
    {
        "product_name": "Cheap Running Shoes",
        "average_rating": 1.6,
        "positive_percent": 0.0,
        "neutral_percent": 0.0,
        "negative_percent": 100.0,
        "score": 16.0,
        "recommendation": "AVOID",
        "recommendation_text": "NO, THIS PRODUCT IS NOT RECOMMENDED",
        "review_count": 5
    }
]

# ------------------------------------------------------------------------------
# Mock Test Cases (Defined before the test loop)
# ------------------------------------------------------------------------------
MOCK_TEST_CASES = [
    # (query, product_pool, expected_product_name)
    ("Budget laptop", mock_laptops, "Budget Laptop"),
    ("I want to buy a budget laptop", mock_laptops, "Budget Laptop"),
    ("Apple MacBook Air", mock_laptops, "Apple MacBook Air"),
    ("I want to buy an Apple MacBook Air", mock_laptops, "Apple MacBook Air"),
    ("MacBook Air", mock_laptops, "Apple MacBook Air"),
    ("Dell Inspiron Laptop", mock_laptops, "Dell Inspiron Laptop"),
    ("laptop", mock_laptops, "Apple MacBook Air"),
    ("I want to buy a laptop", mock_laptops, "Apple MacBook Air"),
    ("Cheap Running Shoes", mock_shoes, "Cheap Running Shoes"),
    ("Nike Running Shoes", mock_shoes, "Nike Running Shoes"),
]

# ------------------------------------------------------------------------------
# Dataset Integration Test Cases (Defined before the test loop)
# ------------------------------------------------------------------------------
DATASET_TEST_CASES = [
    # (query, expected_product_name, expected_rating, expected_decision)
    ("Budget laptop", "Budget Laptop", 1.6, "AVOID"),
    ("I want to buy a budget laptop", "Budget Laptop", 1.6, "AVOID"),
    ("Apple MacBook Air", "Apple MacBook Air", 4.8, "BUY"),
    ("I want to buy an Apple MacBook Air", "Apple MacBook Air", 4.8, "BUY"),
    ("MacBook Air", "Apple MacBook Air", 4.8, "BUY"),
    ("Dell Inspiron Laptop", "Dell Inspiron Laptop", 3.0, "AVOID"),
    ("laptop", "Apple MacBook Air", 4.8, "BUY"),
    ("I want to buy a laptop", "Apple MacBook Air", 4.8, "BUY"),
    ("Cheap Running Shoes", "Cheap Running Shoes", 1.6, "AVOID"),
    ("Nike Running Shoes", "Nike Running Shoes", 4.6, "BUY"),
]


def run_tests():
    print("=" * 70)
    print("TESTING PRODUCT RECOMMENDATION SELECTION LOGIC (test_selection.py)")
    print(f"Project Directory: {PROJECT_DIR}")
    print("=" * 70)

    passed_count = 0
    total_count = 0

    # --------------------------------------------------------------------------
    # Part 1: Mock Product Selection Tests
    # --------------------------------------------------------------------------
    print("\n--- Part 1: Mock Product Selection Tests ---")
    for idx, (query, pool, expected) in enumerate(MOCK_TEST_CASES, 1):
        total_count += 1
        selected = select_recommended_product(pool, query)
        actual = selected["product_name"] if selected else None
        if actual == expected:
            print(f"[PASS] #{idx}: '{query}' -> '{actual}'")
            passed_count += 1
        else:
            print(f"[FAIL] #{idx}: '{query}' -> Expected '{expected}', got '{actual}'")

    # --------------------------------------------------------------------------
    # Part 2: Actual Dataset Integration Tests
    # --------------------------------------------------------------------------
    print("\n--- Part 2: Actual Dataset Integration Tests ---")
    dataset_path = PROJECT_DIR / "dataset" / "product_reviews.csv"
    if not dataset_path.exists():
        print(f"[FAIL] Dataset file not found at: {dataset_path}")
        sys.exit(1)

    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset: {dataset_path.name} ({len(df)} rows)")

    for idx, (query, exp_name, exp_rating, exp_dec) in enumerate(DATASET_TEST_CASES, 1):
        total_count += 1
        res = get_recommendation(df, query)

        if not res.get("found"):
            print(f"[FAIL] Dataset #{idx}: '{query}' -> Recommendation not found (found=False)")
            continue

        bp = res.get("best_product")
        if not bp:
            print(f"[FAIL] Dataset #{idx}: '{query}' -> No best_product returned")
            continue

        actual_name = bp.get("product_name")
        actual_rating = bp.get("average_rating")
        actual_dec = bp.get("recommendation")

        name_ok = actual_name == exp_name
        rating_ok = abs(actual_rating - exp_rating) < 0.1
        dec_ok = actual_dec == exp_dec

        if name_ok and rating_ok and dec_ok:
            print(f"[PASS] Dataset #{idx}: '{query}' -> '{actual_name}' | Rating: {actual_rating} | Decision: {actual_dec}")
            passed_count += 1
        else:
            failures = []
            if not name_ok:
                failures.append(f"Name expected '{exp_name}', got '{actual_name}'")
            if not rating_ok:
                failures.append(f"Rating expected {exp_rating}, got {actual_rating}")
            if not dec_ok:
                failures.append(f"Decision expected '{exp_dec}', got '{actual_dec}'")
            print(f"[FAIL] Dataset #{idx}: '{query}' -> Discrepancy: {'; '.join(failures)}")

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    failed_count = total_count - passed_count
    print(f"SELECTION TESTS COMPLETED: {passed_count}/{total_count} PASSED ({failed_count} FAILED)")
    print("=" * 70)

    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
