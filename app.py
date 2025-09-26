from flask import Flask, request, send_file, render_template_string
import pandas as pd
import re
import io
from ebooklib import epub
from bs4 import BeautifulSoup

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
<title>MCQ Converter</title>
<style>
body { display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial, sans-serif; background: linear-gradient(135deg, #4facfe, #00f2fe); margin: 0; }
.container { text-align: center; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); width: 80%; max-width: 900px; }
h1 { font-size: 36px; margin-bottom: 20px; color: #222; }
textarea { width: 100%; height: 200px; padding: 15px; font-size: 16px; border-radius: 10px; border: 1px solid #ccc; resize: vertical; margin-bottom: 20px; }
input[type=submit], input[type=file] { margin-top: 20px; background: #007bff; color: white; border: none; padding: 15px 30px; font-size: 18px; border-radius: 10px; cursor: pointer; transition: 0.3s; }
input[type=submit]:hover, input[type=file]:hover { background: #0056b3; }
</style>
</head>
<body>
<div class="container">
    <h1>📘 MCQ to Excel Converter</h1>
    <form method="post" action="/convert" enctype="multipart/form-data">
        <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea>
        <br>
        <input type="file" name="mcq_epub" accept=".epub">
        <br>
        <input type="submit" value="Convert to Excel">
    </form>
</div>
</body>
</html>
"""

def extract_text_from_epub(file_storage):
    """Extract all text from EPUB FileStorage object."""
    book = epub.read_epub(file_storage)
    text = ''
    for item in book.get_items():
        if item.get_type() == epub.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text += soup.get_text() + '\n'
    return text

def smart_parse_mcqs(text):
    """Parse MCQs into rows for Excel."""
    text = text.replace('\r\n', '\n').replace('\r','\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    rows = []
    qno = None
    qtext_lines = []
    opts = {}
    answer = None

    for line in lines:
        # Detect options A), B: etc.
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\:\-]\s*(.*)', line)
        if m_opt:
            opts[m_opt.group(1).upper()] = m_opt.group(2).strip()
            continue

        # Detect answers: "Answer: C" or "Ans: B"
        m_ans = re.match(r'^(Answer|Ans)[:\s]*([A-Da-d])$', line, re.IGNORECASE)
        if m_ans:
            answer = m_ans.group(2).upper()
            if qno and opts and answer:
                question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                                f"A) {opts.get('A','')}\nB) {opts.get('B','')}\nC) {opts.get('C','')}\nD) {opts.get('D','')}"
                rows.append([qno, question_full, opts.get('A',''), opts.get('B',''), opts.get('C',''), opts.get('D',''), answer])
            qno = None; qtext_lines=[]; opts={}; answer=None
            continue

        # Detect question number at start like "1. ..." or "12. ..."
        m_q = re.match(r'^(\d+)\.\s*(.*)', line)
        if m_q:
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            continue

        # Continuation of question text
        if qno:
            qtext_lines.append(line)

    return rows

@app.route("/", methods=["GET"])
def index():
    return HTML_FORM

@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()

    # Handle EPUB upload
    if 'mcq_epub' in request.files and request.files['mcq_epub'].filename:
        epub_file = request.files['mcq_epub']
        text += '\n' + extract_text_from_epub(epub_file)

    if not text.strip():
        return "No text or EPUB provided!", 400

    rows = smart_parse_mcqs(text)
    if not rows:
        return "Could not parse any MCQs. Make sure EPUB contains questions in recognizable format.", 400

    # Create Excel file in memory
    df = pd.DataFrame(rows, columns=["Sl.No","Question","A","B","C","D","Correct Answer"])
    output = io.BytesIO()
    df.to_excel(output, index=False, header=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)