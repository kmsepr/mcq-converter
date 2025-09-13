from flask import Flask, request, send_file
import pandas as pd, re, io

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
                background: #f4f6f9;
                margin: 0;
            }
            .container {
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                width: 450px;
            }
            h2 { margin-bottom: 20px; color: #333; }
            input[type=file] { margin: 20px 0; font-size: 16px; }
            input[type=submit] {
                background: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                border-radius: 6px;
                cursor: pointer;
            }
            input[type=submit]:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📘 MCQ to Excel Converter</h2>
            <form method="post" action="/convert" enctype="multipart/form-data">
                <input type="file" name="file" accept=".txt">
                <br>
                <input type="submit" value="Upload & Convert">
            </form>
        </div>
    </body>
    </html>
    """

@app.route('/convert', methods=['POST'])
def convert():
    file = request.files['file']
    text = file.read().decode('utf-8')

    # Each question block ends with answer like "1.C" etc.
    blocks = re.split(r'\n(?=\d+\.)', text)

    rows = []

    def ans_to_num(ans):
        return {"A": 1, "B": 2, "C": 3, "D": 4}.get(ans.upper(), "")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Only keep until the first answer key line (like "12.C")
        block = re.split(r'\n\d+\.[A-D]', block)[0]

        # Extract question number + rest
        match_q = re.match(r'(\d+)\.(.*)', block, re.DOTALL)
        if not match_q:
            continue
        qnum, rest = match_q.groups()

        # Extract options (stop at d)
        options = re.findall(r'([a-d])\)(.*?)(?=\n[a-d]\)|$)', rest, re.DOTALL | re.IGNORECASE)
        opts = {k.lower(): v.strip() for k, v in options}

        # Find answer from original block
        ans_match = re.search(rf'{qnum}\.([A-D])', text)
        ans = ans_match.group(1) if ans_match else ""

        # Question text only (before a)
        qtext_only = re.split(r'\na\)', rest, 1)[0].strip()
        question_full = qtext_only
        for letter in ['a', 'b', 'c', 'd']:
            if letter in opts:
                question_full += f"\n{letter.upper()}) {opts[letter]}"

        rows.append([1, question_full, "A", "B", "C", "D", ans_to_num(ans)])

    df = pd.DataFrame(rows, columns=["1", "Question", "A", "B", "C", "D", "Correct Answer"])

    print(f"✅ Parsed {len(rows)} questions")

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)