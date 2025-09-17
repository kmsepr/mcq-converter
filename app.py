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
    qno = None
    qtext_lines = []
    opts = {}
    answer = None
    explanation_lines = []
    collecting_expl = False

    for line in lines:
        # Match option lines (A,B,C,D)
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\.\s]+\s*(.*)', line)
        if m_opt and not collecting_expl:
            opts[m_opt.group(1).lower()] = m_opt.group(2).strip()
            continue

        # Match answer lines (e.g., 1.C)
        m_ans = re.match(r'^\d+\.\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(1).upper()
            collecting_expl = True  # Everything after this is explanation
            continue

        # Match question start (e.g., "1. Question text")
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q and not collecting_expl:
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            continue

        # Collect explanation lines
        if collecting_expl:
            explanation_lines.append(line)
        elif qno:
            qtext_lines.append(line)

        # If we already have question + options + answer + explanation
        if collecting_expl and (line == lines[-1] or re.match(r'^\d+\.', line)):
            question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
            rows.append([
                1,
                question_full,
                'A','B','C','D',
                {"A":1,"B":2,"C":3,"D":4}[answer],
                "\n".join(explanation_lines).strip()
            ])
            # Reset for next question
            qno, qtext_lines, opts, answer, explanation_lines, collecting_expl = None, [], {}, None, [], False

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()
    if not text:
        return "No text provided!", 400

    rows = parse_mcqs(text)
    if not rows:
        return "Could not parse any MCQs. Please check format.", 400

    df = pd.DataFrame(rows, columns=["1","Question","A","B","C","D","Correct Answer","Explanation"])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)