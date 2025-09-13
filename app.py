from flask import Flask, request, send_file
import pandas as pd
import re
import io

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return """
    <h2>MCQ Converter</h2>
    <form method="post" action="/convert" enctype="multipart/form-data">
        <input type="file" name="file" accept=".txt">
        <br><br>
        <input type="submit" value="Upload & Convert">
    </form>
    """

def parse_mcqs(text):
    """Parse MCQs from text into rows (handles multi-line questions)."""
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

        # Question number
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            # Save previous question
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
            # Start new question
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            opts = {}
            answer = ""
            continue

        # Options a-d
        m_opt = re.match(r'^([a-dA-D])\)\s*(.*)', line)
        if m_opt:
            opts[m_opt.group(1).lower()] = m_opt.group(2)
            continue

        # Answer at end
        m_ans = re.search(r'([A-Da-d])$', line)
        if m_ans and not re.match(r'^[a-dA-D]\)', line):
            answer = m_ans.group(1)
            continue

        # Append extra lines to question text
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
    file = request.files['file']
    text = file.read().decode('utf-8')

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