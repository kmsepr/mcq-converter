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
    <title>MCQ to Excel Converter</title>
    <style>
    body {
        display: flex; justify-content: center; align-items: center;
        height: 100vh; font-family: Arial, sans-serif;
        background: linear-gradient(135deg, #4facfe, #00f2fe); margin: 0;
    }
    .container {
        text-align: center; background: white; padding: 40px;
        border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        width: 80%; max-width: 900px;
    }
    h1 { font-size: 36px; margin-bottom: 20px; color: #222; }
    textarea {
        width: 100%; height: 400px; padding: 15px; font-size: 16px;
        border-radius: 10px; border: 1px solid #ccc; resize: vertical;
        margin-bottom: 20px;
    }
    input[type=submit] {
        margin-top: 20px; background: #007bff; color: white;
        border: none; padding: 15px 30px; font-size: 18px;
        border-radius: 10px; cursor: pointer; transition: 0.3s;
    }
    input[type=submit]:hover { background: #0056b3; }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>📘 MCQ to Excel Converter</h1>
        <form method="post" action="/convert">
            <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea>
            <br>
            <input type="submit" value="Convert to Excel">
        </form>
    </div>
    </body>
    </html>
    """

def parse_mcqs(text):
    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r','\n')
    # remove leading/trailing whitespace lines but keep internal blank lines as separators if needed
    raw_lines = text.split('\n')
    # Trim lines but keep empty ones (for robust detection)
    lines = [l.strip() for l in raw_lines]

    rows = []
    qno = None
    qtext_lines = []
    opts = {}  # keys 'a','b','c','d'
    answer = None
    explanation_lines = []
    capturing_expl = False

    # regex patterns
    # option lines: A:-..., A) ..., (a) ...
    opt_re = re.compile(r'^[\(\[]?([A-Da-d])[\)\:\-\.\s]*\s*(.*)$')
    # answer lines like: 1.A  or 1. A  or 1)A or "Ans: C", "Answer - C"
    qnum_answer_re = re.compile(r'^(\d+)[\.\)]?\s*[:\-]?\s*([A-Da-d])\b\.?$', re.UNICODE)
    ans_label_re = re.compile(r'^(?:Ans(?:wer)?[:\.\-\s]*|Answer[:\.\-\s]*)([A-Da-d])\b\.?$', re.IGNORECASE)
    # lines that are only a single letter answer e.g. "A" (sometimes found) or "A v"
    solo_answer_re = re.compile(r'^([A-Da-d])\s*(?:v)?$', re.UNICODE)
    # 'v' or tick only line
    tick_re = re.compile(r'^[v✔✓]$', re.UNICODE)
    # question start like "1. Question..." or "1:- Question"
    qstart_re = re.compile(r'^(\d+)[\.\)\:\-]\s*(.*)$')

    def flush_question():
        nonlocal qno, qtext_lines, opts, answer, explanation_lines, capturing_expl
        if not qno:
            return
        # Only add row if we have at least one option and an answer
        if opts and answer:
            # Build question text: join question lines
            qtext = '\n'.join([ln for ln in qtext_lines if ln]).strip()
            # Ensure option values exist (empty string if not)
            a_text = opts.get('a', '')
            b_text = opts.get('b', '')
            c_text = opts.get('c', '')
            d_text = opts.get('d', '')
            # Convert answer letter to number 1..4 (if letter present)
            letter = answer.upper() if isinstance(answer, str) else ''
            correct_num = {"A":1,"B":2,"C":3,"D":4}.get(letter, '')
            expl = ' '.join([ln for ln in explanation_lines if ln]).strip()
            rows.append([qno, qtext, a_text, b_text, c_text, d_text, letter, correct_num, expl])
        # reset
        qno = None
        qtext_lines = []
        opts = {}
        answer = None
        explanation_lines = []
        capturing_expl = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip pure tick lines
        if tick_re.match(line):
            i += 1
            continue

        # If line is empty, treat as separator but if we're in question text keep newline
        if line == '':
            # If currently capturing explanation, keep a blank (as paragraph break)
            if capturing_expl:
                explanation_lines.append('')
            elif qno and not opts:
                # blank between question lines: keep as newline in question
                qtext_lines.append('')
            i += 1
            continue

        # Option line
        m_opt = opt_re.match(line)
        if m_opt and not capturing_expl:
            letter = m_opt.group(1).lower()
            opt_text = m_opt.group(2).strip()
            # Option text might continue to next lines (if next lines not an option or question or answer)
            j = i + 1
            cont_lines = []
            while j < len(lines):
                nxt = lines[j]
                if nxt == '':
                    # keep blank as part of option (rare)
                    cont_lines.append('')
                    j += 1
                    continue
                # Stop continuation if next line starts with another option or a question number or looks like an answer
                if opt_re.match(nxt) or qstart_re.match(nxt) or qnum_answer_re.match(nxt) or ans_label_re.match(nxt) or solo_answer_re.match(nxt):
                    break
                # if next line is "v" or tick - stop
                if tick_re.match(nxt):
                    break
                # otherwise it's continuation of option
                cont_lines.append(nxt)
                j += 1
            if cont_lines:
                # append continuation lines
                full_opt = ' '.join([opt_text] + cont_lines).strip()
            else:
                full_opt = opt_text
            opts[letter] = full_opt
            i = j
            continue

        # Answer line with question number appended (e.g., "1.A")
        m_q_ans = qnum_answer_re.match(line)
        if m_q_ans:
            # If qno differs from current, flush previous
            # Many of your samples have the answer line for the same question number,
            # so we set answer and start capturing explanation from next lines.
            # If current qno is different or None, set it from this
            qno_from_line = m_q_ans.group(1)
            ans_letter = m_q_ans.group(2).upper()
            # if this is a new question number and there is an outstanding question, flush previous
            if qno and qno != qno_from_line:
                flush_question()
            qno = qno_from_line
            answer = ans_letter
            capturing_expl = True
            explanation_lines = []
            i += 1
            # skip immediate next line if it's just 'v'
            if i < len(lines) and tick_re.match(lines[i]):
                i += 1
            continue

        # 'Ans: C' style
        m_ans_label = ans_label_re.match(line)
        if m_ans_label:
            ans_letter = m_ans_label.group(1).upper()
            answer = ans_letter
            capturing_expl = True
            explanation_lines = []
            i += 1
            continue

        # Solo answer line (e.g., just "A" or "A v")
        m_solo = solo_answer_re.match(line)
        if m_solo and qno and not capturing_expl and opts:
            answer = m_solo.group(1).upper()
            capturing_expl = True
            explanation_lines = []
            i += 1
            continue

        # Question start line
        m_qstart = qstart_re.match(line)
        if m_qstart:
            # flush previous question if present
            if qno:
                flush_question()
            qno = m_qstart.group(1)
            rest = m_qstart.group(2).strip()
            qtext_lines = [rest] if rest else []
            # if next lines continue the question (not option/answer), include them
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt == '':
                    # preserve blank in question text
                    qtext_lines.append('')
                    j += 1
                    continue
                # stop if next line is an option or answer or next question
                if opt_re.match(nxt) or qstart_re.match(nxt) or qnum_answer_re.match(nxt) or ans_label_re.match(nxt):
                    break
                # else continuation of question
                qtext_lines.append(nxt)
                j += 1
            i = j
            continue

        # If capturing explanation, gather until next question start or a new question number detected
        if capturing_expl:
            # if this line looks like next question starting, flush and continue without consuming it here
            if qstart_re.match(line):
                flush_question()
                continue
            # if next question numeric appears, flush and treat this line as possible question start in next loop
            if re.match(r'^\d+\.', line):
                flush_question()
                continue
            explanation_lines.append(line)
            i += 1
            continue

        # If we have qno and not capturing explanation and this line doesn't match option,
        # it's probably continuation of question text
        if qno and not capturing_expl and not opts:
            qtext_lines.append(line)
            i += 1
            continue

        # If it's none of the above and looks like a numbered leftover (e.g., "2.C" or "2.C\nനിഘണ്ടു..."),
        # try to parse as answer+explanation inline
        m_inline_qans = re.match(r'^(\d+)[\.\)\-]?\s*([A-Da-d])\s*(.*)$', line)
        if m_inline_qans:
            # flush previous if different
            if qno and qno != m_inline_qans.group(1):
                flush_question()
            qno = m_inline_qans.group(1)
            answer = m_inline_qans.group(2).upper()
            rest = m_inline_qans.group(3).strip()
            if rest:
                explanation_lines = [rest]
            else:
                explanation_lines = []
            capturing_expl = True
            i += 1
            continue

        # Fallback: if nothing matched, try to append to current question text
        if qno and not capturing_expl:
            qtext_lines.append(line)
        else:
            # stray lines before first qno -- ignore or could be metadata (like paper title) -- ignore for now
            pass

        i += 1

    # End loop
    # flush last
    if qno:
        flush_question()

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()
    if not text:
        return "No text provided!", 400

    rows = parse_mcqs(text)

    if not rows:
        return "Could not parse any MCQs. Please check format.", 400

    # Columns: Sl.No, Question, A, B, C, D, CorrectLetter, CorrectNumber, Explanation
    df = pd.DataFrame(rows, columns=[
        "Sl.No", "Question", "A", "B", "C", "D",
        "CorrectLetter", "CorrectAnswerNumber", "Explanation"
    ])

    output = io.BytesIO()
    # Write with header and index=False so excel has column names
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)