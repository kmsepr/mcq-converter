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
            .container { text-align: center; background: white; padding: 50px;
                         border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                         width: 700px; max-width: 95%; }
            h1 { font-size: 42px; margin-bottom: 20px; color: #222; }
            p { font-size: 18px; color: #555; margin-bottom: 20px; }
            textarea { width: 100%; height: 200px; padding: 15px; font-size: 16px;
                       border-radius: 10px; border: 1px solid #ccc; resize: vertical;
                       margin-bottom: 20px; }
            input[type=file] { margin: 15px 0; font-size: 16px; }
            input[type=submit] { margin-top: 20px; background: #007bff; color: white;
                                 border: none; padding: 15px 30px; font-size: 18px;
                                 border-radius: 10px; cursor: pointer; transition: 0.3s; }
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
    text = text.replace('\r\n', '\n').replace('\r','\n')
    lines = text.split('\n')

    rows = []
    qno = None
    qtext = ""
    opts = {}
    answer = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Answer line like 4.D
        m_ans = re.match(r'^(\d+)\.\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(2).upper()
            # Save the question
            if qno and opts:
                rows.append([
                    qno,
                    qtext.strip(),
                    opts.get('a',''),
                    opts.get('b',''),
                    opts.get('c',''),
                    opts.get('d',''),
                    answer
                ])
            # Reset
            qno = None
            qtext = ""
            opts = {}
            answer = None
            continue

        # Multi-line options: A) Option text
        m_opt = re.findall(r'([a-dA-D])\)\s*([^a-dA-D]*)', line)
        if m_opt:
            for o, t in m_opt:
                opts[o.lower()] = t.strip()
            continue

        # Inline options: a) ... b) ... c) ... d) ...
        m_inline_opts = re.findall(r'([a-dA-D])\)\s*([^a-dA-D]*)', line)
        if m_inline_opts and not line.startswith(tuple(str(i) for i in range(1,1000))):
            for o, t in m_inline_opts:
                opts[o.lower()] = t.strip()

        # New question line
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            qno = m_q.group(1)
            rest = m_q.group(2).strip()
            # If options are inline
            if any(rest.lower().find(c + ')') != -1 for c in ['a','b','c','d']):
                # Extract options
                opt_parts = re.split(r'([a-dA-D]\))', rest)
                qtext_parts = []
                current_opt = None
                for part in opt_parts:
                    part = part.strip()
                    if not part:
                        continue
                    if re.match(r'^[a-dA-D]\)$', part):
                        current_opt = part[0].lower()
                        opts[current_opt] = ""
                    else:
                        if current_opt:
                            opts[current_opt] += part.strip()
                        else:
                            qtext_parts.append(part.strip())
                qtext = " ".join(qtext_parts)
            else:
                qtext = rest
            continue

        # Continuation of question text
        if qno:
            qtext += " " + line

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()
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

    df = pd.DataFrame(rows, columns=["1","Question","A","B","C","D","Correct Answer"])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)