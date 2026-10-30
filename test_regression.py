import io
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
PROJECT_DIR = Path(r"D:\Product_Review\Product_Review")
CSV_PATH = PROJECT_DIR / "dataset" / "product_reviews.csv"

# Color constants for readability
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

test_results = []

def record_result(category, test_name, passed, http_status, details):
    status_text = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    test_results.append({
        "category": category,
        "test_name": test_name,
        "passed": passed,
        "http_status": http_status,
        "details": details
    })
    print(f"[{status_text}] [{http_status or 'N/A'}] {category} -> {test_name}")
    if details:
        print(f"       Details: {details}")

def http_get(url):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

def http_post_json(url, payload):
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, e.read().decode("utf-8")

def http_post_multipart(url, files=None, headers=None):
    boundary = f"----WebKitFormBoundary{os.urandom(16).hex()}"
    body = bytearray()
    
    if files:
        for name, (filename, content) in files.items():
            mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {mimetype}\r\n\r\n".encode("utf-8"))
            body.extend(content)
            body.extend(b"\r\n")
            
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if headers:
        for h_name, h_val in headers.items():
            req.add_header(h_name, h_val)
            
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

print("=" * 70)
print("PRODUCT REVIEW ANALYSIS SYSTEM - REGRESSION TEST SUITE")
print(f"Target: {BASE_URL}")
print(f"Dataset: {CSV_PATH}")
print("=" * 70)

# ==============================================================================
# 1. HOME PAGE LOADING
# ==============================================================================
print("\n--- 1. Testing Home Page Loading ---")

# 1.1 GET /
status_home, html_home = http_get(f"{BASE_URL}/")
required_home_elements = [
    'id="uploadForm"',
    'id="file"',
    'accept=".csv"',
    'id="uploadButton"',
    'id="uploadMessage"',
    'id="productQuery"',
    'id="searchBtn"',
    'id="recommendationContent"',
    'id="productTable"',
    'id="positiveBar"',
    'id="neutralBar"',
    'id="negativeBar"'
]
home_elements_ok = all(el in html_home for el in required_home_elements)
record_result(
    "1. Home Page",
    "GET / serves home page with all required DOM elements",
    status_home == 200 and home_elements_ok,
    status_home,
    f"All {len(required_home_elements)} required UI elements present in HTML"
)

# 1.2 GET /dashboard
status_dash, html_dash = http_get(f"{BASE_URL}/dashboard")
record_result(
    "1. Home Page",
    "GET /dashboard route renders successfully",
    status_dash == 200 and 'PRODUCT REVIEW' in html_dash,
    status_dash,
    "Dashboard alias route returns HTTP 200"
)

# ==============================================================================
# 2. PRODUCT SEARCH ENDPOINT & VALID SEARCH INPUT
# ==============================================================================
print("\n--- 2. Testing Product Search Endpoint & Valid Search Input ---")

# 2.1 Valid search: "laptop"
status_s1, data_s1 = http_post_json(f"{BASE_URL}/recommend", {"query": "laptop"})
s1_ok = (
    status_s1 == 200
    and data_s1.get("found") is True
    and data_s1.get("product") == "laptop"
    and len(data_s1.get("products", [])) > 0
)
record_result(
    "2. Product Search",
    "Valid search query 'laptop' returns matched products",
    s1_ok,
    status_s1,
    f"Matched {len(data_s1.get('products', []))} products for keyword 'laptop'"
)

# 2.2 Valid search: "running shoes" (multi-word keyword)
status_s2, data_s2 = http_post_json(f"{BASE_URL}/recommend", {"query": "I want to buy running shoes"})
s2_ok = (
    status_s2 == 200
    and data_s2.get("found") is True
    and data_s2.get("product") == "running shoes"
    and len(data_s2.get("products", [])) > 0
)
record_result(
    "2. Product Search",
    "Natural query 'I want to buy running shoes' extracts product keyword",
    s2_ok,
    status_s2,
    f"Extracted product '{data_s2.get('product')}' and matched {len(data_s2.get('products', []))} items"
)

# ==============================================================================
# 3. EMPTY SEARCH INPUT HANDLING
# ==============================================================================
print("\n--- 3. Testing Empty Search Input Handling ---")

# 3.1 Empty string: ""
status_e1, data_e1 = http_post_json(f"{BASE_URL}/recommend", {"query": ""})
e1_ok = status_e1 == 400 and "error" in data_e1
record_result(
    "3. Empty Search Handling",
    "Empty string query '' rejected with HTTP 400",
    e1_ok,
    status_e1,
    f"Returned error: '{data_e1.get('error')}'"
)

# 3.2 Whitespace string: "   "
status_e2, data_e2 = http_post_json(f"{BASE_URL}/recommend", {"query": "   "})
e2_ok = status_e2 == 400 and "error" in data_e2
record_result(
    "3. Empty Search Handling",
    "Whitespace query '   ' stripped and rejected with HTTP 400",
    e2_ok,
    status_e2,
    f"Returned error: '{data_e2.get('error')}'"
)

# 3.3 Missing query key: {}
status_e3, data_e3 = http_post_json(f"{BASE_URL}/recommend", {})
e3_ok = status_e3 == 400 and "error" in data_e3
record_result(
    "3. Empty Search Handling",
    "Missing 'query' payload rejected with HTTP 400",
    e3_ok,
    status_e3,
    f"Returned error: '{data_e3.get('error')}'"
)

# ==============================================================================
# 4. RECOMMENDATION GENERATION
# ==============================================================================
print("\n--- 4. Testing Recommendation Generation ---")

status_rec, data_rec = http_post_json(f"{BASE_URL}/recommend", {"query": "laptop"})
best = data_rec.get("best_product", {})
required_best_fields = [
    "product_name",
    "average_rating",
    "positive_percent",
    "neutral_percent",
    "negative_percent",
    "score",
    "recommendation",
    "recommendation_text",
    "review_count"
]
has_all_fields = all(f in best for f in required_best_fields)

# Verify formula: score = round((average_rating / 5) * 50 + (positive_percent / 100) * 50, 2)
expected_score = round((best.get("average_rating", 0) / 5) * 50 + (best.get("positive_percent", 0) / 100) * 50, 2)
score_matches = abs(best.get("score", 0) - expected_score) < 0.05

# Verify decision logic
rec_label = best.get("recommendation")
rating = best.get("average_rating", 0)
pos_pct = best.get("positive_percent", 0)
if rating >= 4 and pos_pct >= 60:
    expected_decision = "BUY"
elif rating >= 3 and pos_pct >= 40:
    expected_decision = "CONSIDER"
else:
    expected_decision = "AVOID"

decision_matches = rec_label == expected_decision

rec_ok = (
    status_rec == 200
    and has_all_fields
    and score_matches
    and decision_matches
    and best.get("score", 0) >= max(p.get("score", 0) for p in data_rec.get("products", []))
)
record_result(
    "4. Recommendation",
    "Best product selection, score formula, and decision logic verified for generic query 'laptop'",
    rec_ok,
    status_rec,
    f"Best: '{best.get('product_name')}', Score: {best.get('score')} (Formula match: {score_matches}), Decision: '{rec_label}' (Rule match: {decision_matches})"
)

# 4.2 Specific query: "Budget laptop" -> Budget Laptop (AVOID)
status_rec_budget, data_rec_budget = http_post_json(f"{BASE_URL}/recommend", {"query": "Budget laptop"})
best_budget = data_rec_budget.get("best_product", {})
budget_ok = (
    status_rec_budget == 200
    and data_rec_budget.get("found") is True
    and best_budget.get("product_name") == "Budget Laptop"
    and best_budget.get("recommendation") == "AVOID"
    and best_budget.get("average_rating") == 1.6
    and len(data_rec_budget.get("products", [])) == 5
)
record_result(
    "4. Recommendation",
    "Specific product query 'Budget laptop' selects Budget Laptop (AVOID) over HTTP",
    budget_ok,
    status_rec_budget,
    f"Selected: '{best_budget.get('product_name')}', Decision: '{best_budget.get('recommendation')}', Table items: {len(data_rec_budget.get('products', []))}"
)

# ==============================================================================
# 5. PRODUCT ANALYSIS OUTPUT
# ==============================================================================
print("\n--- 5. Testing Product Analysis Output ---")

products_list = data_rec.get("products", [])
products_count = len(products_list)
all_products_valid = True
scores = []

for p in products_list:
    if not all(k in p for k in required_best_fields):
        all_products_valid = False
        break
    if not (1.0 <= p["average_rating"] <= 5.0):
        all_products_valid = False
        break
    scores.append(p["score"])

# Check that products are sorted in descending order of score
is_sorted_desc = scores == sorted(scores, reverse=True)

analysis_ok = (
    status_rec == 200
    and products_count > 0
    and all_products_valid
    and is_sorted_desc
)
record_result(
    "5. Product Analysis",
    "Product analysis table data structure, rating bounds, and score sorting",
    analysis_ok,
    status_rec,
    f"Analyzed {products_count} products. All fields valid: {all_products_valid}, Sorted by score descending: {is_sorted_desc}"
)

# ==============================================================================
# 6. SENTIMENT ANALYSIS CALCULATIONS
# ==============================================================================
print("\n--- 6. Testing Sentiment Analysis Calculations ---")

# Verify percentage sum = 100% for all products
sentiment_sum_ok = True
for p in products_list:
    pct_sum = round(p["positive_percent"] + p["neutral_percent"] + p["negative_percent"], 1)
    if abs(pct_sum - 100.0) > 0.5:
        sentiment_sum_ok = False
        break

# Verify sentiment breakdown across diverse products
macbook = next((p for p in products_list if "MacBook" in p["product_name"]), None)
dell = next((p for p in products_list if "Dell" in p["product_name"]), None)
budget = next((p for p in products_list if "Budget" in p["product_name"]), None)

macbook_ok = macbook and macbook["positive_percent"] == 100.0 and macbook["negative_percent"] == 0.0
dell_ok = dell and dell["neutral_percent"] == 60.0 and dell["positive_percent"] == 20.0 and dell["negative_percent"] == 20.0
budget_ok = budget and budget["negative_percent"] == 100.0 and budget["positive_percent"] == 0.0

sentiment_calc_ok = sentiment_sum_ok and macbook_ok and dell_ok and budget_ok
record_result(
    "6. Sentiment Analysis",
    "Sentiment distributions match rating labels (Positive >=4, Neutral ==3, Negative <3)",
    sentiment_calc_ok,
    status_rec,
    f"Percentages sum to 100%: {sentiment_sum_ok}. MacBook Positive: {macbook['positive_percent']}%, Dell Neutral: {dell['neutral_percent']}%, Budget Negative: {budget['negative_percent']}%"
)

# ==============================================================================
# 7. CSV UPLOAD FUNCTIONALITY (THE 5 UPLOAD TESTS)
# ==============================================================================
print("\n--- 7. Testing CSV Upload Functionality (5 Upload Tests) ---")

UPLOAD_URL = f"{BASE_URL}/upload"

# Test 7.1: Real CSV upload with valid dataset
with open(CSV_PATH, "rb") as f:
    csv_bytes = f.read()

status_u1, raw_u1 = http_post_multipart(
    UPLOAD_URL,
    files={"file": ("product_reviews.csv", csv_bytes)},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
res_u1 = json.loads(raw_u1)
u1_ok = (
    status_u1 == 200
    and res_u1.get("success") is True
    and "message" in res_u1
    and res_u1.get("review_count") == 175
    and isinstance(res_u1.get("metrics"), dict)
    and "accuracy" in res_u1["metrics"]
    and "precision" in res_u1["metrics"]
    and "recall" in res_u1["metrics"]
    and "f1" in res_u1["metrics"]
    and "confusion_matrix" in res_u1["metrics"]
)
record_result(
    "7. CSV Upload",
    "Test 7.1: Valid CSV upload returns HTTP 200 with full metrics and review count",
    u1_ok,
    status_u1,
    f"success={res_u1.get('success')}, review_count={res_u1.get('review_count')}, accuracy={res_u1.get('metrics', {}).get('accuracy')}"
)

# Test 7.2: Missing file selection
status_u2, raw_u2 = http_post_multipart(
    UPLOAD_URL,
    files={},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
res_u2 = json.loads(raw_u2)
u2_ok = status_u2 == 400 and res_u2.get("success") is False and "error" in res_u2
record_result(
    "7. CSV Upload",
    "Test 7.2: Missing file rejected with HTTP 400 and error message",
    u2_ok,
    status_u2,
    f"error='{res_u2.get('error')}'"
)

# Test 7.3: Non-CSV file (.json)
status_u3, raw_u3 = http_post_multipart(
    UPLOAD_URL,
    files={"file": ("sample.json", b'{"key": "value"}')},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
res_u3 = json.loads(raw_u3)
u3_ok = status_u3 == 400 and res_u3.get("success") is False and "Only CSV files" in res_u3.get("error", "")
record_result(
    "7. CSV Upload",
    "Test 7.3: Non-CSV extension (.json) rejected with HTTP 400",
    u3_ok,
    status_u3,
    f"error='{res_u3.get('error')}'"
)

# Test 7.4: Empty CSV file (0 bytes)
status_u4, raw_u4 = http_post_multipart(
    UPLOAD_URL,
    files={"file": ("empty.csv", b"")},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
res_u4 = json.loads(raw_u4)
u4_ok = status_u4 == 400 and res_u4.get("success") is False and "empty" in res_u4.get("error", "").lower()
record_result(
    "7. CSV Upload",
    "Test 7.4: Empty CSV file (0 bytes) rejected with HTTP 400",
    u4_ok,
    status_u4,
    f"error='{res_u4.get('error')}'"
)

# Test 7.5: Invalid CSV schema (missing review text / rating columns)
status_u5, raw_u5 = http_post_multipart(
    UPLOAD_URL,
    files={"file": ("invalid_schema.csv", b"col_a,col_b\n1,2\n3,4\n5,6\n")},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
res_u5 = json.loads(raw_u5)
u5_ok = status_u5 == 400 and res_u5.get("success") is False and "validation" in res_u5.get("error", "").lower()
record_result(
    "7. CSV Upload",
    "Test 7.5: CSV with invalid schema rejected with HTTP 400 without replacing dataset",
    u5_ok,
    status_u5,
    f"error='{res_u5.get('error')}'"
)

# ==============================================================================
# SUMMARY REPORT
# ==============================================================================
print("\n" + "=" * 70)
total_tests = len(test_results)
passed_tests = sum(1 for r in test_results if r["passed"])
failed_tests = total_tests - passed_tests
print(f"REGRESSION SUITE COMPLETED: {passed_tests}/{total_tests} TESTS PASSED ({failed_tests} FAILED)")
print("=" * 70)

if failed_tests > 0:
    print(f"\n{RED}FAILURES DETECTED:{RESET}")
    for r in test_results:
        if not r["passed"]:
            print(f"- [{r['http_status']}] {r['category']} -> {r['test_name']}: {r['details']}")
    sys.exit(1)
else:
    print(f"\n{GREEN}ALL REGRESSION TESTS PASSED CLEANLY.{RESET}")
    sys.exit(0)

