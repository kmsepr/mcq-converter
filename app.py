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
                padding: 50px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                width: 700px;
                max-width: 95%;
            }
            h1 {
                font-size: 42px;
                margin-bottom: 20px;
                color: #222;
            }
            p {
                font-size: 18px;
                color: #555;
                margin-bottom: 20px;
            }
            textarea {
                width: 100%;
                height: 200px;
                padding: 15px;
                font-size: 16px;
                border-radius: 10px;
                border: 1px solid #ccc;
                resize: vertical;
                margin-bottom: 20px;
            }
            input[type=file] {
                margin: 15px 0;
                font-size: 16px;
            }
            input[type=submit] {
                margin-top: 20px;
                background: #007bff;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 10px;
                cursor: pointer;
                transition: 0.3s;
            }
            input[type=submit]:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📘 MCQ to Excel Converter</h1>
            <p>Paste your MCQs below or upload a .txt file.</p>
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

@app.route('/convert', methods=['POST'])
def convert():
    # First try pasted text
    text = request.form.get("mcq_text", "").strip()

    # If no text was pasted, try file upload
    if not text and 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            text = file.read().decode('utf-8')

    if not text:
        return "No text or file provided!", 400

    # Pattern to capture: Qn, options a-d, and answer like "1.C"
    pattern = re.compile(
        r'(\d+)\.(.*?)\n\s*a\)(.*?)\n\s*b\)(.*?)\n\s*c\)(.*?)\n\s*d\)(.*?)\n\s*\d+\.\s*([A-D])',
        re.DOTALL | re.IGNORECASE
    )

    matches = pattern.findall(text)

    def ans_to_num(ans):
        return {"A": 1, "B": 2, "C": 3, "D": 4}.get(ans.upper(), "")

    rows = []
    for qno, qtext, opt_a, opt_b, opt_c, opt_d, ans_letter in matches:
        question_full = f"{qtext.strip()}\nA) {opt_a.strip()}\nB) {opt_b.strip()}\nC) {opt_c.strip()}\nD) {opt_d.strip()}"
        rows.append([1, question_full, "A", "B", "C", "D", ans_to_num(ans_letter)])

    if not rows:
        return "No valid MCQs found in the input.", 400

    df = pd.DataFrame(rows, columns=["1", "Question", "A", "B", "C", "D", "Correct Answer"])

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)