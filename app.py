from flask import Flask, request, send_file, render_template_string
import pandas as pd
import io

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>MCQ Converter</title>
<style>
body { font-family: Arial; display:flex; justify-content:center; align-items:center; height:100vh; background:#f0f0f0; }
.container { background:white; padding:30px; border-radius:15px; box-shadow:0 10px 20px rgba(0,0,0,0.2); width:90%; max-width:800px; }
textarea { width:100%; height:200px; margin-bottom:15px; padding:10px; font-size:14px; }
input[type=file], input[type=submit] { margin:5px 0; padding:10px; font-size:16px; }
</style>
</head>
<body>
<div class="container">
<h2>📘 MCQ Converter</h2>

<h3>Paste MCQs as Text</h3>
<form method="post" action="/convert_text">
<textarea name="mcq_text" placeholder="Paste MCQs here..."></textarea><br>
<input type="submit" value="Convert to Excel">
</form>

<hr>

<h3>Upload MCQs CSV/Excel</h3>
<form method="post" action="/convert_file" enctype="multipart/form-data">
<input type="file" name="mcq_file" accept=".csv, .xlsx, .xls"><br>
<input type="submit" value="Convert File">
</form>
</div>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/convert_file", methods=["POST"])
def convert_file():
    f = request.files.get("mcq_file")
    if not f:
        return "No file selected!", 400

    # Read file
    if f.filename.endswith(".csv"):
        df = pd.read_csv(f)
    else:
        df = pd.read_excel(f)

    # Export as Excel
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

@app.route("/convert_text", methods=["POST"])
def convert_text():
    # Your text parser here
    return "Text conversion not implemented yet."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)