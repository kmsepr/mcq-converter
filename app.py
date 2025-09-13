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
                background: linear-gradient(135deg, #4facfe, #00f2fe);
                margin: 0;
            }
            .container {
                text-align: center;
                background: white;
                padding: 70px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                width: 700px;
                max-width: 95%;
            }
            h1 { font-size: 40px; margin-bottom: 15px; color: #222; }
            p { font-size: 20px; color: #444; margin-bottom: 40px; }
            input[type=file] { margin: 25px 0; font-size: 18px; }
            input[type=submit] {
                background: #007bff; color: white; border: none;
                padding: 18px 36px; font-size: 20px;
                border-radius: 10px; cursor: pointer; transition: 0.3s;
            }
            input[type=submit]:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📘 MCQ to Excel Converter</h1>
            <p>Upload your .txt file and download a clean Excel file with only questions & answers.</p>
            <form method="post" action="/convert" enctype="multipart/form-data">
                <input type="file" name="file" accept=".txt">
                <br><br>
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

    # Split into blocks on numbers like "1.", "2." etc.
    blocks = re.split(r'\n(?=\d+\.)', text)

    rows = []

    def ans_to_num(ans):
        return {"A": 1, "B": 2, "C": 3, "D": 4}.get(ans.upper(), "")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Stop before any explanation (cut after first answer key)
        block_cut = re.split(r'\n\d+\.[A-D]', block)[0]

        # Extract Q number + text
        match_q = re.match(r'(\d+)\.(.*)', block_cut, re.DOTALL)
        if not match_q:
            continue
        qnum, rest = match_q.groups()

        # Extract options
        options = re.findall(r'([a-d])\)(.*?)(?=\n[a-d]\)|$)', rest, re.DOTALL | re.IGNORECASE)
        opts = {k.lower(): v.strip() for k, v in options}

        # Find correct answer from the original block (like "12.C")
        ans_match = re.search(rf'{qnum}\.([A-D])', block)
        ans = ans_match.group(1) if ans_match else ""

        # Build ONE single string (question + options)
        qtext_only = re.split(r'\na\)', rest, 1)[0].strip()
        question_full = qtext_only
        for letter in ['a', 'b', 'c', 'd']:
            if letter in opts:
                question_full += f"\n{letter.upper()}) {opts[letter]}"

        # Add row: all content stays in Column 2
        rows.append([1, question_full.strip(), "A", "B", "C", "D", ans_to_num(ans)])

    # DataFrame
    df = pd.DataFrame(rows, columns=["1", "Question", "A", "B", "C", "D", "Correct Answer"])

    print(f"✅ Parsed {len(rows)} questions")

    # Return Excel
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)