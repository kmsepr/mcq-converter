from flask import Flask, request, send_file
import pandas as pd
import re
import io

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    # The HTML template for the user interface, styled using custom CSS
    return """
    <!DOCTYPE html>
    <html>
    <head>
    <title>MCQ Converter</title>
    <style>
    body {
        display: flex; justify-content: center; align-items: center;
        height: 100vh; font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #4facfe, #00f2fe); margin: 0;
    }
    .container {
        text-align: center; background: white; padding: 40px;
        border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        width: 90%; max-width: 900px;
        transition: all 0.3s ease;
    }
    @media (min-width: 768px) {
        .container {
            width: 80%;
        }
    }
    h1 { 
        font-size: 36px; margin-bottom: 20px; color: #1e40af; 
        font-weight: 700;
    }
    textarea {
        width: 100%; height: 400px; padding: 15px; font-size: 16px;
        border-radius: 10px; border: 2px solid #e5e7eb; resize: vertical;
        margin-bottom: 20px; box-sizing: border-box;
    }
    input[type=submit] {
        margin-top: 20px; background: #3b82f6; color: white;
        border: none; padding: 15px 30px; font-size: 18px;
        border-radius: 10px; cursor: pointer; transition: 0.3s;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4);
        font-weight: 600;
    }
    input[type=submit]:hover { 
        background: #2563eb; 
        box-shadow: 0 6px 15px rgba(37, 99, 235, 0.5);
    }
    .instructions {
        text-align: left;
        margin-top: 20px;
        padding: 15px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background-color: #f9fafb;
        color: #4b5563;
        font-size: 14px;
    }
    .instructions strong {
        color: #1f2937;
    }
    </style>
    <!-- Load Inter font for aesthetics -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    </head>
    <body>
    <div class="container">
        <h1>📘 MCQ to Excel Converter</h1>
        <form method="post" action="/convert">
            <textarea name="mcq_text" placeholder="Paste your MCQs here...
Example format:
1. What is the capital of France?
A) Berlin
B) London
C) Paris
D) Rome
1.C

2. Which planet is known as the Red Planet?
A) Venus
B) Mars
C) Jupiter
D) Saturn
2.B

(The converter will also try to capture explanations after the answer key.)
"></textarea>
            <div class="instructions">
                <strong>Formatting Guide:</strong>
                <ul>
                    <li>Questions must start with a number followed by a period (e.g., <strong>1.</strong>, <strong>12.</strong>)</li>
                    <li>Options must start with <strong>A)</strong>, <strong>B)</strong>, <strong>C)</strong>, <strong>D)</strong> (or similar variations like A:, (A), etc.)</li>
                    <li>The Answer Key must be on a new line and follow the format: <strong>[Question Number].[Correct Option Letter]</strong> (e.g., <strong>1.C</strong>)</li>
                    <li>Output will be in four columns: **Column A: Serial No. (Preserved), Column B: Question/Options (Combined), Column C: Correct Answer Index (1=A), Column D: Explanation**</li>
                </ul>
            </div>
            <input type="submit" value="Convert to Excel">
        </form>
    </div>
    </body>
    </html>
    """

def parse_mcqs(text):
    """
    Parses raw text containing MCQs, options, answer keys, and explanations
    into a structured list of lists.
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r','\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    rows = []
    qno = None
    qtext_lines = []
    opts = {}
    answer = None
    explanation_lines = []
    capturing_expl = False
    
    for line in lines:
        # 1. Check for new question start (resets state)
        m_q_start = re.match(r'^(\d+)\.(.*)', line)
        if m_q_start:
            # If we were processing a previous question, finalize it
            if qno and answer:
                # Compile the full question text including options
                question_full = '\n'.join(qtext_lines).strip()
                
                # Format options for the combined output column (Column B)
                opt_display = "\n"
                for key in ['a', 'b', 'c', 'd']:
                    opt_display += f"{key.upper()}) {opts.get(key, 'N/A')}\n"
                
                # Map option letter to numerical index (1=A, 2=B, etc.) (Column C)
                correct_answer_index = {"A":1,"B":2,"C":3,"D":4}.get(answer, 0)

                # Store the data: [A, B, C, D] where B-D are combined/processed fields
                rows.append([
                    qno, # 0 -> Column A: Serial Number
                    question_full + opt_display.strip(), # 1 -> Column B: Question and Options
                    opts.get('a',''), # 2 (Discarded)
                    opts.get('b',''), # 3 (Discarded)
                    opts.get('c',''), # 4 (Discarded)
                    opts.get('d',''), # 5 (Discarded)
                    correct_answer_index, # 6 -> Column C: Correct Index
                    ' '.join(explanation_lines).strip() # 7 -> Column D: Explanation
                ])
                
            # Start new question
            qno = m_q_start.group(1)
            qtext_lines = [m_q_start.group(2).strip()]
            opts = {}
            answer = None
            explanation_lines = []
            capturing_expl = False
            continue
        
        # 2. Match option lines (A), A:, (a), etc.
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\:\-\s]*\s*(.*)', line)
        if m_opt and not capturing_expl:
            opt_letter_lower = m_opt.group(1).lower()
            opt_text = m_opt.group(2).strip()
            
            opt_text = re.sub(r'^[\.\)\:\-\s]+', '', opt_text)
            
            if opt_text and opt_letter_lower not in opts:
                opts[opt_letter_lower] = opt_text
            
            if len(opts) == 4:
                 capturing_expl = False
            continue

        # 3. Match answer key lines (e.g., 1.C)
        m_ans = re.match(r'^(\d+)\.\s*([A-Da-d])$', line)
        if m_ans:
            if m_ans.group(1) == qno:
                answer = m_ans.group(2).upper()
                capturing_expl = True # Start capturing explanation after this line
                explanation_lines = [] # Reset explanation
                continue
        
        # 4. If in explanation mode, append line
        if capturing_expl:
            explanation_lines.append(line)
            continue

        # 5. Continuation of question text (if no option or answer key was matched)
        if qno and not opts and not answer:
            qtext_lines.append(line)
        # Handle question text that might appear between options
        elif qno and not answer and len(opts) < 4:
             qtext_lines.append(line)


    # Finalize the last question outside the loop
    if qno and answer:
        question_full = '\n'.join(qtext_lines).strip()
        
        opt_display = "\n"
        for key in ['a', 'b', 'c', 'd']:
            opt_display += f"{key.upper()}) {opts.get(key, 'N/A')}\n"

        correct_answer_index = {"A":1,"B":2,"C":3,"D":4}.get(answer, 0)
        
        rows.append([
            qno, 
            question_full + opt_display.strip(), 
            opts.get('a',''), 
            opts.get('b',''), 
            opts.get('c',''), 
            opts.get('d',''), 
            correct_answer_index, 
            ' '.join(explanation_lines).strip()
        ])

    return rows

@app.route('/convert', methods=['POST'])
def convert():
    # Retrieve text from the form
    text = request.form.get("mcq_text", "").strip()
    if not text:
        return "No text provided!", 400

    # Parse the text into rows 
    # [SlNo(A), FullQ&A(B), OptA, OptB, OptC, OptD, CorrectIdx(C), Expl(D)]
    full_rows = parse_mcqs(text)

    if not full_rows:
        return "Could not parse any MCQs. Please check the formatting guide in the input area.", 400

    # Filter the data to match the required four-column structure:
    # Column A: Sl.No (Index 0)
    # Column B: Question and Options (Index 1)
    # Column C: Correct Option Number (Index 6)
    # Column D: Explanation (Index 7)
    
    # Select the required columns from the full_rows list
    required_data = [
        [row[0], row[1], row[6], row[7]]
        for row in full_rows
    ]

    # Create DataFrame (header used only internally for debugging, not in final Excel)
    df = pd.DataFrame(required_data, columns=[
        "Serial Number",
        "Question and Options",
        "Correct Option Number",
        "Explanation"
    ])
    
    # Use io.BytesIO to create an in-memory file
    output = io.BytesIO()
    # Write the DataFrame to Excel format
    # Use header=False to ensure only the raw data is in the output file
    df.to_excel(output, index=False, header=False) 
    output.seek(0)
    
    # Send the file back to the client
    return send_file(
        output,
        as_attachment=True,
        download_name="mcqs_converted.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    # Standard entry point for Flask apps
    app.run(host='0.0.0.0', port=3000)
