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
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #4facfe, #00f2fe);
                margin: 0;
            }
            .container {
                text-align: center;
                background: white;
                padding: 50px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                width: 700px;
                max-width: 95%;
            }
            h1 { font-size: 42px; margin-bottom: 20px; color: #222; }
            p { font-size: 18px; color: #555; margin-bottom: 20px; }
            textarea {
                width: 100%; height: 200px; padding: 15px; font-size: 16px;
                border-radius: 10px; border: 1px solid #ccc; resize: vertical;
                margin-bottom: 20px;
            }
            input[type=file] { margin: 15px 0; font-size: 16px; }
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
            <p>Paste your MCQs or upload a .txt file.</p>
            <form method="post" action="/convert" enctype="multipart/form-data">
                <textarea name="mcq_text" placeholder="Paste your questions here..."></textarea>
                <br>
                <input type="file" name="file" accept=".txt">
                <br>
                <input type="submit" value="Convert to Excel">
            </form>
        </div>
    </body>
    </html>
    """

def parse_mcqs(text):
    """Parse MCQs from text into rows (supports multi-line questions)."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    rows = []

    qno = ""
    qtext_lines = []
    opts = {}
    answer = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match question number
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            if qno and opts and answer:
                question_full = ' '.join(qtext_lines).strip()
                rows.append([
                    qno,
                    question_full,
                    opts.get('a',''),
                    opts.get('b',''),
                    opts.get('c',''),
                    opts.get('d',''),
                    {"A":1,"B":2,"C":3,"D":4}.get(answer.upper(),"")
                ])
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            opts = {}
            answer = ""
            continue

        # Match options a-d
        m_opt = re.match(r'^([a-dA-D])\)\s*(.*)', line)
        if m_opt:
            opts[m_opt.group(1).lower()] = m_opt.group(2)
            continue

        # Match answer
        m_ans = re.search(r'([A-Da-d])$', line)
        if m_ans and not re.match(r'^[a-dA-D]\)', line):
            answer = m_ans.group(1)
            continue

        # Append extra lines to question
        if not re.match(r'^[a-dA-D]\)', line):
            qtext_lines.append(line)

    # Add last question
    if qno and opts and answer:
        question_full = ' '.join(qtext_lines).strip()
        rows.append([
            qno,
            question_full,
            opts.get('a',''),
            opts.get('b',''),
            opts.get('c',''),
            opts.get('d',''),
            {"A":1,"B":2,"C":3,"D":4}.get(answer.upper(),"")
        ])

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    # Use pasted text first
    text = request.form.get("mcq_text", "").strip()

    # If no paste, use uploaded file
    if not text and 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            try:
                text = file.read().decode('utf-8')
            except UnicodeDecodeError:
                return "Failed to read the uploaded file. Ensure UTF-8 encoding.", 400

    if not text:
        return "No text or file provided!", 400

    rows = parse_mcqs(text)
    if not rows:
        return "No valid MCQs found.", 400

    df = pd.DataFrame(rows, columns=["Q.No","Question","A","B","C","D","Correct Answer"])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)