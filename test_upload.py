import urllib.request
import json
import mimetypes
import uuid
from pathlib import Path

URL = "http://127.0.0.1:5000/upload"
CSV_PATH = Path(r"d:\Product_Review\Product_Review\dataset\product_reviews.csv")

def post_multipart(url, fields=None, files=None, headers=None):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    
    if fields:
        for k, v in fields.items():
            body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))
            
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

print("=== Running End-to-End Tests against http://127.0.0.1:5000/upload ===")

# Test 1: Real CSV upload with X-Requested-With
with open(CSV_PATH, "rb") as f:
    csv_bytes = f.read()

status, text = post_multipart(
    URL,
    files={"file": ("product_reviews.csv", csv_bytes)},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
print(f"Test 1 - Real CSV Upload:\n  Status: {status}\n  Response: {text}\n")
res1 = json.loads(text)

assert status == 200, f"Expected 200, got {status}"
assert res1.get("success") is True, f"Expected success=True, got {res1.get('success')}"
assert "message" in res1, "Missing 'message' in response"
assert "review_count" in res1, "Missing 'review_count' in response"
assert "metrics" in res1, "Missing 'metrics' in response"
assert res1["review_count"] == 175, f"Expected 175 reviews, got {res1['review_count']}"
assert "accuracy" in res1["metrics"], "Missing 'accuracy' in metrics"

# Test 2: Rejection of missing file
status, text = post_multipart(
    URL,
    files={},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
print(f"Test 2 - Missing File:\n  Status: {status}\n  Response: {text}\n")
res2 = json.loads(text)
assert status == 400
assert res2.get("success") is False
assert "error" in res2

# Test 3: Rejection of non-CSV file
status, text = post_multipart(
    URL,
    files={"file": ("test.json", b'{"key": "value"}')},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
print(f"Test 3 - Non-CSV File:\n  Status: {status}\n  Response: {text}\n")
res3 = json.loads(text)
assert status == 400
assert res3.get("success") is False
assert "error" in res3

# Test 4: Rejection of empty CSV file
status, text = post_multipart(
    URL,
    files={"file": ("empty.csv", b"")},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
print(f"Test 4 - Empty CSV File:\n  Status: {status}\n  Response: {text}\n")
res4 = json.loads(text)
assert status == 400
assert res4.get("success") is False
assert "empty" in res4.get("error").lower()

# Test 5: Rejection of CSV with invalid schema (e.g. missing review text column)
status, text = post_multipart(
    URL,
    files={"file": ("invalid_schema.csv", b"col_a,col_b\n1,2\n3,4\n5,6\n")},
    headers={"X-Requested-With": "XMLHttpRequest"}
)
print(f"Test 5 - Invalid CSV Schema:\n  Status: {status}\n  Response: {text}\n")
res5 = json.loads(text)
assert status == 400
assert res5.get("success") is False
assert "validation" in res5.get("error").lower()

print(">>> ALL 5 END-TO-END UPLOAD TESTS PASSED SUCCESSFULLY! <<<")