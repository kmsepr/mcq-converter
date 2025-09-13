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

    pattern = re.compile(
        r'(\d+)\.(.*?)\n(a\).*?\n.*?b\).*?\n.*?c\).*?\n.*?d\).*?\n\s*(\d+)\.([A-D])',
        re.DOTALL | re.IGNORECASE
    )
    matches = pattern.findall(text)

    def ans_to_num(ans):
        return {"A": 1, "B": 2, "C": 3, "D": 4}.get(ans.upper(), "")

    rows = []
    for qno, qtext, _, _, _, ans_qno, ans_letter in matches:
        rows.append([1, qtext.strip(), "A", "B", "C", "D", ans_to_num(ans_letter)])

    df = pd.DataFrame(rows, columns=["1", "Question", "A", "B", "C", "D", "Correct Answer"])

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)