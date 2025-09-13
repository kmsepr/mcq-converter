from flask import Flask, request, send_file
import pandas as pd, re, io

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

@app.route('/convert', methods=['POST'])
def convert():
    file = request.files['file']
    text = file.read().decode('utf-8')

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
        # Build question string including options
        question_full = f"{qtext.strip()}\nA) {opt_a.strip()}\nB) {opt_b.strip()}\nC) {opt_c.strip()}\nD) {opt_d.strip()}"
        rows.append([1, question_full, "A", "B", "C", "D", ans_to_num(ans_letter)])

    df = pd.DataFrame(rows, columns=["1", "Question", "A", "B", "C", "D", "Correct Answer"])

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)