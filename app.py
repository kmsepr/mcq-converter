from flask import Flask, request, send_file
import pandas as pd
import re
import io

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return """
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
    textarea {
        width: 100%; height: 400px; padding: 15px; font-size: 16px;
        border-radius: 10px; border: 1px solid #ccc; resize: vertical;
        margin-bottom: 20px;
    }
    input[type=submit] {
        margin-top: 20px; background: #007bff; color: white;
        border: none; padding: 15px 30px; font-size: 18px;
        border-radius: 10px; cursor: pointer; transition: 0.3s;
    }
    input[type=submit]:hover { background: #0056b3; }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>📘 MCQ to Excel Converter</h1>
        <form method="post" action="/convert">
            <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea>
            <br>
            <input type="submit" value="Convert to Excel">
        </form>
    </div>
    </body>
    </html>
    """

def parse_mcqs(text):
    text = text.replace('\r\n', '\n').replace('\r','\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    rows = []
    qtext_lines = []
    opts = {}
    answer = None
    collecting_expl = False

    for i, line in enumerate(lines):
        # Match option lines (A,B,C,D)
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\.\s]+\s*(.*)', line)
        if m_opt and not collecting_expl:
            opts[m_opt.group(1).upper()] = m_opt.group(2).strip()
            continue

        # Match answer lines (e.g., 1.C or 1.D)
        m_ans = re.match(r'^\d+\.\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(1).upper()
            collecting_expl = True
            continue

        # Match question start (strip leading number like "1.")
        m_q = re.match(r'^\d+\.(.*)', line)
        if m_q and not collecting_expl and not opts:
            qtext_lines = [m_q.group(1).strip()]
            continue

        if not collecting_expl:
            qtext_lines.append(line)

        # Finalize when we hit a new question or end of input
        if collecting_expl and (i == len(lines)-1 or re.match(r'^\d+\.', lines[i+1])):
            question_full = "\n".join(qtext_lines).strip()
            question_full += "\n" + \
                f"A) {opts.get('A','')}\nB) {opts.get('B','')}\nC) {opts.get('C','')}\nD) {opts.get('D','')}"

            rows.append([
                1,                                      # Column A
                question_full,                          # Column B (question + options)
                "A", "B", "C", "D",                     # Columns C–F
                {"A":1,"B":2,"C":3,"D":4}[answer],      # Column G (correct option index)
                ""                                      # Column H (image URL, kept blank)
            ])
            # Reset for next question
            qtext_lines, opts, answer, collecting_expl = [], {}, None, False

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()
    if not text:
        return "No text provided!", 400

    rows = parse_mcqs(text)
    if not rows:
        return "Could not parse any MCQs. Please check format.", 400

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    # Write WITHOUT headers
    df.to_excel(output, index=False, header=False, engine="openpyxl")
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="mcqs.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)