import shutil
import uuid
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, url_for

from model import prepare_dataframe, train_model
from recommendation import get_recommendation

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
DATASET_PATH = DATASET_DIR / "product_reviews.csv"

df = pd.DataFrame()
model_info = {}


def load_dataset():
    global df, model_info

    DATASET_DIR.mkdir(exist_ok=True)

    if not DATASET_PATH.exists():
        df = pd.DataFrame()
        model_info = {
            "error": "Dataset not found."
        }
        return

    try:
        df, model_info = train_model(str(DATASET_PATH))
        print("Dataset loaded successfully.")
        print("Model information:", model_info)

    except Exception as exc:
        df = pd.DataFrame()
        model_info = {
            "error": str(exc)
        }

        print("Model training error:", exc)


# Load dataset when application starts
load_dataset()


@app.route("/")
def home():
    status = request.args.get("status")
    message = request.args.get("message")
    return render_template("index.html", status=status, message=message)


@app.route("/dashboard")
def dashboard():
    status = request.args.get("status")
    message = request.args.get("message")
    return render_template("index.html", status=status, message=message)


@app.route("/recommend", methods=["POST"])
def recommend():

    if df.empty:
        return jsonify({
            "found": False,
            "message": "Dataset is empty. Please upload a CSV dataset."
        }), 400

    data = request.get_json(silent=True) or {}

    user_query = str(
        data.get("query", "")
    ).strip()

    # Fallback to form parameters if submitted via regular form
    if not user_query and request.form:
        user_query = str(
            request.form.get("product", "") or request.form.get("query", "")
        ).strip()

    if not user_query:
        return jsonify({
            "error": "Please enter what product you want to buy."
        }), 400

    try:
        result = get_recommendation(
            df,
            user_query
        )

        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "error": str(exc)
        }), 500


@app.route("/upload", methods=["POST"])
def upload():

    global df, model_info

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )

    file = request.files.get("file")

    # 1. Validate file selection
    if not file or not file.filename or not file.filename.strip():
        err_msg = "Please select a CSV file."
        print("[UPLOAD] Rejected: No file selected.")
        if is_ajax:
            return jsonify({
                "success": False,
                "error": err_msg
            }), 400
        return redirect(url_for("home", status="error", message=err_msg))

    # 2. Validate file extension
    if not file.filename.lower().endswith(".csv"):
        err_msg = "Only CSV files (.csv) are allowed."
        print(f"[UPLOAD] Rejected: Invalid file extension for '{file.filename}'.")
        if is_ajax:
            return jsonify({
                "success": False,
                "error": err_msg
            }), 400
        return redirect(url_for("home", status="error", message=err_msg))

    DATASET_DIR.mkdir(exist_ok=True)
    temp_path = DATASET_DIR / f"temp_upload_{uuid.uuid4().hex[:8]}.csv"
    backup_path = DATASET_DIR / "product_reviews.csv.bak"

    try:
        # 3. Save to staging file first - original dataset is untouched
        file.save(temp_path)

        # 4. Validate file is not empty
        if temp_path.stat().st_size == 0:
            temp_path.unlink(missing_ok=True)
            err_msg = "The selected CSV file is empty."
            print(f"[UPLOAD] Rejected: Empty file '{file.filename}'.")
            if is_ajax:
                return jsonify({
                    "success": False,
                    "error": err_msg
                }), 400
            return redirect(url_for("home", status="error", message=err_msg))

        # 5. Validate CSV can be parsed
        try:
            uploaded_df = pd.read_csv(temp_path)
        except Exception as read_exc:
            temp_path.unlink(missing_ok=True)
            err_msg = f"Invalid CSV format: {str(read_exc)}"
            print(f"[UPLOAD] Rejected: CSV parsing error: {read_exc}")
            if is_ajax:
                return jsonify({
                    "success": False,
                    "error": err_msg
                }), 400
            return redirect(url_for("home", status="error", message=err_msg))

        # 6. Validate dataset columns and required structure
        try:
            prepare_dataframe(uploaded_df)
        except Exception as prep_exc:
            temp_path.unlink(missing_ok=True)
            err_msg = f"CSV validation error: {str(prep_exc)}"
            print(f"[UPLOAD] Rejected: Dataframe validation failed: {prep_exc}")
            if is_ajax:
                return jsonify({
                    "success": False,
                    "error": err_msg
                }), 400
            return redirect(url_for("home", status="error", message=err_msg))

        # 7. Train model on the temporary validated dataset
        try:
            new_df, new_model_info = train_model(str(temp_path))
        except Exception as train_exc:
            temp_path.unlink(missing_ok=True)
            err_msg = f"Model training failed: {str(train_exc)}"
            print(f"[UPLOAD ERROR] Training failed: {train_exc}")
            if is_ajax:
                return jsonify({
                    "success": False,
                    "error": err_msg
                }), 400
            return redirect(url_for("home", status="error", message=err_msg))

        # 8. Create backup of current dataset before replacement
        if DATASET_PATH.exists():
            shutil.copy2(DATASET_PATH, backup_path)

        # 9. Replace the dataset file only after validation and training succeed
        shutil.move(str(temp_path), str(DATASET_PATH))

        # 10. Update active application state
        df = new_df
        model_info = new_model_info

        review_count = len(df)
        success_msg = f"Dataset uploaded successfully! Model retrained on {review_count} reviews."
        print(f"[UPLOAD] Success: '{file.filename}' processed. Reviews: {review_count}.")

        if is_ajax:
            return jsonify({
                "success": True,
                "message": success_msg,
                "review_count": review_count,
                "metrics": model_info.get("metrics")
            }), 200

        return redirect(url_for("home", status="success", message=success_msg))

    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

        # Restore original dataset and model state if backup exists and dataset was affected
        if backup_path.exists() and (not DATASET_PATH.exists() or DATASET_PATH.stat().st_size == 0):
            try:
                shutil.copy2(backup_path, DATASET_PATH)
                df, model_info = train_model(str(DATASET_PATH))
                print("[UPLOAD] Restored previous dataset and model after failure.")
            except Exception as restore_exc:
                print(f"[RESTORE ERROR] Failed to restore backup: {restore_exc}")

        err_msg = f"Failed to process CSV file: {str(exc)}"
        print(f"[UPLOAD ERROR] Unexpected error: {exc}")

        if is_ajax:
            return jsonify({
                "success": False,
                "error": err_msg
            }), 400

        return redirect(url_for("home", status="error", message=err_msg))


if __name__ == "__main__":
    app.run(
        debug=False,
        host="127.0.0.1",
        port=5000
    )