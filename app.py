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
    }
    form { text-align: center; }
    textarea { width: 600px; height: 400px; }
    </style>
    </head>
    <body>
        <form action="/convert" method="post">
            <h2>Paste your MCQs below:</h2>
            <textarea name="mcqs"></textarea><br><br>
            <button type="submit">Convert to Excel</button>
        </form>
    </body>
    </html>
    """

@app.route("/convert", methods=["POST"])
def convert():
    text = request.form["mcqs"]

    # --- Extract answers like 1.C, 2.A, 3.D ---
    answer_pattern = r"(\d+)\.([A-Da-d])"
    answers = dict((int(num), letter.upper()) for num, letter in re.findall(answer_pattern, text))

    # --- Extract question blocks ---
    # Capture text starting with "1." until next number
    question_pattern = r"(\d+)\.(.*?)(?=\n\d+\.|$)"
    question_blocks = re.findall(question_pattern, text, re.DOTALL)

    rows = []
    for qnum, block in question_blocks:
        qnum = int(qnum)
        block = block.strip()

        # Split question + options
        # Look for lines starting with a/b/c/d
        options = re.findall(r"[\na-d][\)\:\-\.]\s*(.*)", block, re.IGNORECASE)
        question_text = re.split(r"\n\s*[a-d][\)\:\-]", block, 1, re.IGNORECASE)[0].strip()

        if len(options) < 4:
            # Skip if options not found properly
            continue

        # Rebuild full question with options
        question_full = (
            f"{question_text.strip()}\n"
            f"a) {options[0].strip()}\n"
            f"b) {options[1].strip()}\n"
            f"c) {options[2].strip()}\n"
            f"d) {options[3].strip()}"
        )

        # Find correct answer number
        correct_letter = answers.get(qnum, "")
        correct_num = {"A": 1, "B": 2, "C": 3, "D": 4}.get(correct_letter, "")

        # Fill Excel row (B=question, G=correct)
        row = ["", question_full, "", "", "", "", correct_num, "", "", ""]
        rows.append(row)

    # --- Create Excel ---
    df = pd.DataFrame(rows, columns=list("ABCDEFGHIJ"))
    output = io.BytesIO()
    df.to_excel(output, index=False, header=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="mcqs.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)