# Product Review Analysis

Beginner-friendly full-stack NLP application using Flask, Pandas, NLTK, TF-IDF, One-Hot Encoding and Logistic Regression.

## Project structure

```text
Product_Review/
│
├── app.py
├── preprocessing.py
├── model.py
├── requirements.txt
├── README.md
│
├── dataset/
│   └── product_reviews.csv
│
├── models/
│   └── generated model files
│
├── templates/
│   └── index.html
│
└── static/
    └── style.css
```

## Run in VS Code on Windows

Open the project folder in VS Code.

### 1. Create virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again.

### 3. Install packages

```powershell
pip install -r requirements.txt
```

### 4. Start the application

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

The first run downloads the NLTK English stopword list if necessary.

## Dataset

Put your CSV at:

```text
dataset/product_reviews.csv
```

Recommended columns:

```text
product_id, product_name, category, product_type, rating, review_text, gender, price, sentiment
```

`price` is optional in this simple version.

If `sentiment` is missing, it is generated from rating:

- 4-5 = Positive
- 3 = Neutral
- 1-2 = Negative

## NLP flow

Review text
→ lowercase
→ remove URLs/punctuation
→ tokenize
→ remove stopwords
→ stemming
→ TF-IDF

Categorical data
→ One-Hot Encoding

TF-IDF + One-Hot features
→ Logistic Regression
→ Positive / Neutral / Negative

## API examples

### GET /

Redirects to the dashboard.

### GET /dashboard

Displays the dashboard.

### POST /predict

JSON:

```json
{
  "review": "The product quality is excellent",
  "category": "Clothes",
  "product_type": "Shirt",
  "gender": "Male"
}
```

Response:

```json
{
  "review": "The product quality is excellent",
  "sentiment": "Positive"
}
```

### POST /upload

Upload a CSV using multipart/form-data with the field name:

```text
file
```

The server saves the CSV, preprocesses it and retrains the model automatically.

## Important note

The model is intentionally simple for academic/project demonstration. Accuracy depends heavily on the quality and size of the dataset. A tiny dataset should not be treated as a production-grade sentiment model.
