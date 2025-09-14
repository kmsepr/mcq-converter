from flask import Flask, request, render_template_string

app = Flask(__name__)

def format_mcqs(text):
    lines = text.strip().split("\n")
    output_lines = []
    qno = None
    statements = []
    options = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Question start
        if line[0].isdigit() and "." in line:
            if qno:  # save previous question
                if statements or options:
                    output_lines.append(f"{qno}.Q?")
                    for s in statements:
                        output_lines.append(s)
                    for o in options:
                        output_lines.append(o)
            qno = line.split(".")[0]
            statements = []
            options = []
            continue

        # Statements like i, ii, iii
        if line.lower().startswith(("i", "ii", "iii", "iv")):
            statements.append(line)
            continue

        # Options A–D
        if line[0].lower() in ["a", "b", "c", "d"]:
            options.append(line)
            continue

        # Answer
        if line.split(".")[0].isdigit() and line[-1].upper() in ["A","B","C","D"]:
            output_lines.append(line)
            continue

    # Last question
    if qno:
        output_lines.append(f"{qno}.Q?")
        for s in statements:
            output_lines.append(s)
        for o in options:
            output_lines.append(o)

    return "\n".join(output_lines)


@app.route("/", methods=["GET","POST"])
def index():
    output = ""
    if request.method == "POST":
        content = request.form.get("content","")
        output = format_mcqs(content)

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCQ Formatter</title>
        <style>
            body { font-family: Arial, sans-serif; background:#f4f7fb; padding:30px; }
            h2 { text-align:center; }
            .box { max-width:900px; margin:auto; background:white; padding:30px; border-radius:15px; box-shadow:0 4px 12px rgba(0,0,0,0.2); }
            textarea { width:100%; height:400px; font-size:16px; padding:15px; border-radius:8px; border:1px solid #ccc; resize:vertical; }
            button { margin-top:15px; background:#007bff; color:white; border:none; padding:12px 25px; font-size:16px; border-radius:8px; cursor:pointer; }
            button:hover { background:#0056b3; }
            pre { white-space: pre-wrap; font-size:16px; background:#f9f9f9; padding:15px; border-radius:8px; border:1px solid #ddd; margin-top:20px; }
            .copy-btn { background:#28a745; margin-left:10px; }
            .copy-btn:hover { background:#1e7e34; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>📘 MCQ Formatter</h2>
            <form method="post">
                <textarea name="content" placeholder="Paste your raw MCQs here...">{{request.form.get('content','')}}</textarea><br>
                <button type="submit">Format</button>
            </form>
            {% if output %}
                <h3>Formatted Output</h3>
                <button class="copy-btn" onclick="copyText()">📋 Copy Output</button>
                <pre id="result">{{output}}</pre>
            {% endif %}
        </div>
        <script>
            function copyText(){
                var text = document.getElementById("result").innerText;
                navigator.clipboard.writeText(text);
                alert("Copied to clipboard!");
            }
        </script>
    </body>
    </html>
    """, output=output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)