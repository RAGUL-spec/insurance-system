from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import PyPDF2
from anthropic import Anthropic
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Anthropic client
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key:
    client = Anthropic(api_key=anthropic_key)
else:
    client = None
    print("WARNING: No Anthropic API key found!")

# Policy requirements
POLICY_REQUIREMENTS = {
    "required_fields": [
        "patient_name",
        "patient_id",
        "policy_number",
        "date_of_service",
        "doctor_name",
        "doctor_license_number",
        "diagnosis",
        "treatment_description",
        "total_cost",
        "hospital_name"
    ]
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def analyze_document_with_ai(document_text, required_fields):
    if not client:
        return {"extracted_data": {}}

    prompt = f"""
You are analyzing a medical insurance document.
Extract the following fields:

{json.dumps(required_fields, indent=2)}

Document text:
{document_text}

Return ONLY valid JSON in this exact format:
{{
  "extracted_data": {{
    "patient_name": null,
    "patient_id": null,
    "policy_number": null,
    "date_of_service": null,
    "doctor_name": null,
    "doctor_license_number": null,
    "diagnosis": null,
    "treatment_description": null,
    "total_cost": null,
    "hospital_name": null
  }}
}}
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        start = response_text.find("{")
        end = response_text.rfind("}") + 1

        if start != -1 and end > start:
            return json.loads(response_text[start:end])

    except Exception as e:
        print(f"AI error: {e}")

    return {"extracted_data": {}}

def validate_claim(extracted_data, required_fields):
    results = {
        "completion_percentage": 0,
        "matched_fields": [],
        "missing_fields": [],
        "eligibility_status": "pending"
    }

    matched = 0
    total = len(required_fields)

    for field in required_fields:
        value = extracted_data.get(field)

        if value and str(value).lower() not in ["null", "none", ""]:
            matched += 1
            results["matched_fields"].append({
                "field": field.replace("_", " ").title(),
                "value": str(value),
                "status": "valid"
            })
        else:
            results["missing_fields"].append({
                "field": field.replace("_", " ").title(),
                "reason": "Field not found in document"
            })

    results["completion_percentage"] = round((matched / total) * 100)

    if results["completion_percentage"] == 100:
        results["eligibility_status"] = "eligible"
    elif results["completion_percentage"] >= 70:
        results["eligibility_status"] = "review_required"
    else:
        results["eligibility_status"] = "insufficient_documentation"

    return results

@app.route("/api/upload", methods=["POST"])
def upload_files():
    if "documents" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist("documents")
    if not files or files[0].filename == "":
        return jsonify({"error": "No files selected"}), 400

    all_text = ""

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

            if filename.lower().endswith(".pdf"):
                all_text += extract_text_from_pdf(path) + "\n"

    if not all_text.strip():
        return jsonify({"error": "No text extracted"}), 400

    ai_result = analyze_document_with_ai(
        all_text,
        POLICY_REQUIREMENTS["required_fields"]
    )

    extracted_data = ai_result.get("extracted_data", {})
    validation = validate_claim(
        extracted_data,
        POLICY_REQUIREMENTS["required_fields"]
    )

    return jsonify(validation), 200

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )

