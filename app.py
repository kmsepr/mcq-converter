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
    textarea { width: 600px; height: 300px; }
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

    # Pattern: Question, Options, Answer
    pattern = r"(.*?)\nA\)(.*?)\nB\)(.*?)\nC\)(.*?)\nD\)(.*?)\nAnswer\s*:\s*([ABCD])"
    matches = re.findall(pattern, text, re.DOTALL)

    rows = []
    for idx, (q, a, b, c, d, ans) in enumerate(matches, start=1):
        question_full = f"{q.strip()}\nA){a.strip()}\nB){b.strip()}\nC){c.strip()}\nD){d.strip()}"
        correct_num = {"A": 1, "B": 2, "C": 3, "D": 4}[ans]

        # Fill only Column B and G, leave rest blank
        row = ["", question_full, "", "", "", "", correct_num, "", "", ""]
        rows.append(row)

    # Create DataFrame with 10 columns (A–J)
    df = pd.DataFrame(rows, columns=list("ABCDEFGHIJ"))

    output = io.BytesIO()
    df.to_excel(output, index=False, header=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="mcqs.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(debug=True, port=8000)