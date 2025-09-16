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
    body { display: flex; justify-content: center; align-items: center;
        height: 100vh; font-family: Arial, sans-serif;
        background: linear-gradient(135deg, #4facfe, #00f2fe); margin: 0; }
    .container { text-align: center; background: white; padding: 40px;
        border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        width: 80%; max-width: 900px; }
    h1 { font-size: 36px; margin-bottom: 20px; color: #222; }
    textarea { width: 100%; height: 200px; padding: 15px; font-size: 16px;
        border-radius: 10px; border: 1px solid #ccc; resize: vertical;
        margin-bottom: 20px; }
    input, select { margin-top: 20px; background: #007bff; color: white;
        border: none; padding: 10px 20px; font-size: 16px;
        border-radius: 10px; cursor: pointer; transition: 0.3s; }
    input:hover { background: #0056b3; }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>📘 MCQ Converter</h1>
        <form method="post" action="/convert" enctype="multipart/form-data">
            <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea>
            <br>
            OR upload CSV: <input type="file" name="mcq_file" accept=".csv">
            <br>
            Output format:
            <select name="format">
                <option value="excel">Excel (.xlsx)</option>
                <option value="csv">CSV (.csv)</option>
            </select>
            <br>
            <input type="submit" value="Convert">
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

    for line in lines:
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\.]\s*(.*)', line)
        if m_opt:
            opts[m_opt.group(1).lower()] = m_opt.group(2).strip()
            continue
        m_ans = re.match(r'^\d+\.\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(1).upper()
            if qno and opts and answer:
                question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                    f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
                rows.append([
                    1,
                    question_full,
                    'A','B','C','D',
                    {"A":1,"B":2,"C":3,"D":4}[answer]
                ])
            qno = None
            qtext_lines = []
            opts = {}
            answer = None
            continue
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            continue
        if qno:
            qtext_lines.append(line)
    return rows

@app.route('/convert', methods=['POST'])
def convert():
    mcq_text = request.form.get("mcq_text", "").strip()
    mcq_file = request.files.get("mcq_file")
    output_format = request.form.get("format", "excel")

    rows = []

    if mcq_file and mcq_file.filename.endswith('.csv'):
        df = pd.read_csv(mcq_file)
        # Assume CSV has columns: Question, A, B, C, D, Answer (letter)
        for _, row in df.iterrows():
            rows.append([
                1,
                row.get('Question',''),
                row.get('A',''),
                row.get('B',''),
                row.get('C',''),
                row.get('D',''),
                {"A":1,"B":2,"C":3,"D":4}.get(row.get('Answer','').upper(), 0)
            ])
    elif mcq_text:
        rows = parse_mcqs(mcq_text)
    else:
        return "No input provided!", 400

    if not rows:
        return "No MCQs could be parsed!", 400

    df_out = pd.DataFrame(rows, columns=["1","Question","A","B","C","D","Correct Answer"])
    output = io.BytesIO()

    if output_format == 'csv':
        df_out.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.csv", mimetype="text/csv")
    else:
        df_out.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)