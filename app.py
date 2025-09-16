from flask import Flask, request, send_file, render_template_string
import pandas as pd
import re
import io

app = Flask(__name__)

# HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>MCQ Converter</title>
<style>
body {
    display: flex; justify-content: center; align-items: center;
    height: 100vh; font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #4facfe, #00f2fe); margin: 0;
}
.container {
    text-align: center; background: white; padding: 40px;
    border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    width: 80%; max-width: 900px;
}
h1 { font-size: 36px; margin-bottom: 20px; color: #222; }
textarea { width: 100%; height: 300px; padding: 15px; font-size: 16px;
    border-radius: 10px; border: 1px solid #ccc; resize: vertical; margin-bottom: 20px;
}
input[type=submit], button {
    margin-top: 20px; background: #007bff; color: white;
    border: none; padding: 15px 30px; font-size: 18px;
    border-radius: 10px; cursor: pointer; transition: 0.3s;
}
input[type=submit]:hover, button:hover { background: #0056b3; }
</style>
</head>
<body>
<div class="container">
    <h1>📘 MCQ Converter</h1>

    <h3>1️⃣ Convert MCQs from Text</h3>
    <form method="post" action="/convert_text">
        <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea>
        <br>
        <label>Download as:</label>
        <select name="file_type">
            <option value="excel">Excel (.xlsx)</option>
            <option value="csv">CSV (.csv)</option>
        </select>
        <br>
        <input type="submit" value="Convert Text">
    </form>
    <hr>
    <h3>2️⃣ Convert MCQs from CSV Upload</h3>
    <form method="post" action="/convert_csv" enctype="multipart/form-data">
        <input type="file" name="mcq_file" accept=".csv">
        <br><br>
        <label>Download as:</label>
        <select name="file_type">
            <option value="excel">Excel (.xlsx)</option>
            <option value="csv">CSV (.csv)</option>
        </select>
        <br>
        <input type="submit" value="Convert CSV">
    </form>
</div>
</body>
</html>
"""

# Parsing MCQs from text
def parse_mcqs(text):
    text = text.replace('\r\n', '\n').replace('\r','\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    rows = []
    qno = None
    qtext_lines = []
    opts = {}
    answer = None

    for line in lines:
        # Option lines (A-D)
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\.]\s*(.*)', line)
        if m_opt:
            opts[m_opt.group(1).lower()] = m_opt.group(2).strip()
            continue

        # Answer line (e.g., 12.C)
        m_ans = re.match(r'^\d+\.\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(1).upper()
            if qno and opts and answer:
                question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                    f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
                rows.append([
                    qno,
                    question_full,
                    opts.get('a',''),
                    opts.get('b',''),
                    opts.get('c',''),
                    opts.get('d',''),
                    {"A":1,"B":2,"C":3,"D":4}[answer]
                ])
            qno = None
            qtext_lines = []
            opts = {}
            answer = None
            continue

        # Question line
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            continue

        # Continuation of question
        if qno:
            qtext_lines.append(line)

    return rows

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML)

# Route for text paste conversion
@app.route("/convert_text", methods=["POST"])
def convert_text():
    text = request.form.get("mcq_text", "").strip()
    file_type = request.form.get("file_type", "excel")

    if not text:
        return "No text provided!", 400

    rows = parse_mcqs(text)
    if not rows:
        return "No MCQs found in text!", 400

    df = pd.DataFrame(rows, columns=["QNo","Question","A","B","C","D","Correct Answer"])
    output = io.BytesIO()

    if file_type == "csv":
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.csv", mimetype="text/csv")
    else:
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

# Route for CSV upload conversion
@app.route("/convert_csv", methods=["POST"])
def convert_csv():
    file = request.files.get("mcq_file")
    file_type = request.form.get("file_type", "excel")

    if not file or not file.filename.endswith('.csv'):
        return "No valid CSV uploaded!", 400

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return f"Error reading CSV: {e}", 400

    output = io.BytesIO()
    if file_type == "csv":
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.csv", mimetype="text/csv")
    else:
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)