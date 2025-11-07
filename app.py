import os, io, re, time, random, json, threading, subprocess, logging
from collections import deque
from logging.handlers import RotatingFileHandler
from flask import Flask, request, send_file, Response, render_template_string, abort, stream_with_context
import pandas as pd

# ==============================================================
# 🧠 Basic Config
# ==============================================================

app = Flask(__name__)
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# ==============================================================
# 📘 MCQ Converter (unchanged except slight pandas optimization)
# ==============================================================

def parse_mcqs(text):
    text = text.replace('\r', '\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    rows, qno, qtext_lines, opts, answer, explanation_lines = [], None, [], {}, None, []
    capturing_expl = False

    for line in lines:
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\:\-]*\s*(.*)', line)
        if m_opt and not capturing_expl:
            opts[m_opt.group(1).lower()] = re.sub(r'^[\.\)\:\-\s]+', '', m_opt.group(2).strip())
            continue
        m_ans = re.match(r'^(\d+)\.\s*(?:Answer|Ans)?[:\-]?\s*([A-Da-d])$', line)
        if m_ans:
            answer, qno, capturing_expl, explanation_lines = m_ans.group(2).upper(), m_ans.group(1), True, []
            continue
        if capturing_expl:
            if re.match(r'^\d+\.', line):
                if opts and answer:
                    question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                        f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
                    rows.append([qno, question_full, 'A','B','C','D',
                                 {"A":1,"B":2,"C":3,"D":4}[answer],
                                 ' '.join(explanation_lines).strip(), ""])
                qno, qtext_lines, opts, answer, capturing_expl = None, [], {}, None, False
                m_q = re.match(r'^(\d+)\.(.*)', line)
                if m_q:
                    qno, qtext_lines = m_q.group(1), [m_q.group(2).strip()]
                continue
            else:
                explanation_lines.append(line); continue
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q: qno, qtext_lines = m_q.group(1), [m_q.group(2).strip()]; continue
        if qno: qtext_lines.append(line)

    if opts and answer:
        question_full = '\n'.join(qtext_lines).strip() + '\n' + \
            f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
        rows.append([qno, question_full, 'A','B','C','D',
                     {"A":1,"B":2,"C":3,"D":4}[answer],
                     ' '.join(explanation_lines).strip(), ""])
    return rows


@app.route("/mcq")
def index_mcq():
    return """<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<title>MCQ Converter</title>
<style>body{font-family:sans-serif;text-align:center;margin:0;background:#eef}
textarea{width:95%;height:350px;margin:10px;border-radius:8px}
button{padding:10px 20px;margin:10px;border:0;border-radius:8px;background:#28a;color:#fff;font-size:16px}
</style></head><body><h2>📘 MCQ → Excel</h2>
<form method=post action=/convert><textarea name=mcq_text></textarea><br><button>Convert</button></form></body></html>"""


@app.route("/convert", methods=["POST"])
def convert():
    text = request.form.get("mcq_text", "").strip()
    if not text: return "No text!", 400
    rows = parse_mcqs(text)
    if not rows: return "Parse error!", 400
    df = pd.DataFrame(rows, columns=[
        "Sr. No.","Question Text","Option 1","Option 2","Option 3","Option 4",
        "Correct Option Number (1–4)","Explanation","Image URL"
    ])
    output = io.BytesIO(); df.to_excel(output, index=False); output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

# ==============================================================
# 🎶 YouTube Playlist Radio SECTION
# ==============================================================

LOG_PATH = "/mnt/data/radio.log"
COOKIES_PATH = "/mnt/data/cookies.txt"
CACHE_FILE = "/mnt/data/playlist_cache.json"
os.makedirs("/mnt/data/radio_cache", exist_ok=True)
handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=1)
logging.getLogger().addHandler(handler)

PLAYLISTS = {
    "kas_ranker": "https://youtube.com/playlist?list=PLS2N6hORhZbuZsS_2u5H_z6oOKDQT1NRZ",
    "eftguru": "https://youtube.com/playlist?list=PLYKzjRvMAycgYvPysx_tiv0q-ZHnDJx0y",
    "firdous": "https://youtube.com/playlist?list=PLgkREi1Wpr-VMfNuvrgNhZqpjEbT7nxv0",
    "samastha": "https://youtube.com/playlist?list=PLgkREi1Wpr-XgNxocxs3iPj61pqMhi9bv",
}

PLAY_MODES = {"kas_ranker": "reverse", "eftguru": "normal", "firdous": "normal", "samastha": "normal"}

STREAMS_RADIO = {}
MAX_QUEUE = 96  # smaller buffer → less RAM
REFRESH_INTERVAL = 14400  # 4 hr

# ==============================================================
# 🧩 Playlist Caching
# ==============================================================

def load_cache_radio():
    try: return json.load(open(CACHE_FILE))
    except: return {}

def save_cache_radio(data):
    try: json.dump(data, open(CACHE_FILE, "w"))
    except: pass

CACHE_RADIO = load_cache_radio()

def get_playlist_ids(url):
    try:
        cmd = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--no-warnings", "--quiet", url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return [e["id"] for e in data.get("entries", []) if "id" in e]
    except Exception as e:
        logging.warning(f"Playlist read fail: {e}")
        return []

def load_playlist_ids_radio(name, url):
    ids = get_playlist_ids(url)
    if not ids: return CACHE_RADIO.get(name, [])
    mode = PLAY_MODES.get(name, "normal")
    if mode == "reverse": ids.reverse()
    elif mode == "shuffle": random.shuffle(ids)
    CACHE_RADIO[name] = ids; save_cache_radio(CACHE_RADIO)
    return ids

# ==============================================================
# 🎧 Low-CPU Sequential Worker
# ==============================================================

def stream_worker_radio(name):
    s = STREAMS_RADIO[name]

    # =========================================================
    # ⚙️ Tunable lightweight parameters
    # =========================================================
    MAX_QUEUE = 5                  # keep very small buffer
    FFMPEG_BITRATE = "40k"         # reduce CPU & RAM load
    REFRESH_INTERVAL = 7200        # refresh playlist every 2h
    RETRY_SLEEP = 8                # wait time after any failure
    TRACK_GAP = 2                  # short gap between tracks

    last_refresh = 0
    start_time = time.time()

    while True:
        try:
            # =========================================================
            # 🔁 Refresh playlist if empty or too old
            # =========================================================
            if not s.get("IDS") or (time.time() - last_refresh) > REFRESH_INTERVAL:
                logging.info(f"[{name}] 🔄 Refreshing playlist IDs...")
                ids = load_playlist_ids_radio(name, PLAYLISTS[name])
                if ids:
                    s["IDS"] = ids
                    last_refresh = time.time()
                    logging.info(f"[{name}] ✅ Loaded {len(ids)} videos.")
                else:
                    logging.warning(f"[{name}] ⚠️ No playlist IDs found, retrying...")
                    time.sleep(RETRY_SLEEP)
                    continue

            ids = s["IDS"]
            vid = ids[s["INDEX"] % len(ids)]
            s["INDEX"] = (s["INDEX"] + 1) % len(ids)
            url = f"https://www.youtube.com/watch?v={vid}"
            logging.info(f"[{name}] ▶️ Streaming: {url}")

            # =========================================================
            # 🎧 yt-dlp + ffmpeg lightweight pipeline
            # =========================================================
            cmd = (
                f'yt-dlp -f "bestaudio/best" --no-playlist --quiet --no-warnings '
                f'--limit-rate 200K --user-agent "Mozilla/5.0" '
                f'-o - "{url}" | '
                f'ffmpeg -loglevel quiet -i pipe:0 -ac 1 -ar 44100 '
                f'-b:a {FFMPEG_BITRATE} -f mp3 pipe:1'
            )

            # =========================================================
            # 🧩 Sequential single-process stream
            # =========================================================
            with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
                for chunk in iter(lambda: proc.stdout.read(4096), b''):
                    if not chunk:
                        break
                    # keep queue minimal for RAM efficiency
                    while len(s["QUEUE"]) >= MAX_QUEUE:
                        time.sleep(0.1)
                    s["QUEUE"].append(chunk)

                proc.wait()

            logging.info(f"[{name}] ✅ Finished track, next in {TRACK_GAP}s...")
            time.sleep(TRACK_GAP)

            # =========================================================
            # ♻️ Restart every 6 hours to prevent leaks
            # =========================================================
            if (time.time() - start_time) > 21600:
                logging.info(f"[{name}] ♻️ Restarting worker to free memory...")
                break

        except Exception as e:
            logging.error(f"[{name}] ❌ Worker error: {e}")
            time.sleep(RETRY_SLEEP)

# ==============================================================
# 🌐 Flask Routes
# ==============================================================

@app.route("/")
def home():
    html = """<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<style>body{background:#000;color:#0f0;font-family:monospace;text-align:center}
a{display:block;color:#0f0;border:1px solid #0f0;margin:6px;padding:10px;border-radius:8px;text-decoration:none}
a:hover{background:#0f0;color:#000}</style></head><body><h3>🎧 YouTube Radio</h3>
<a href='/mcq'>🧠 MCQ Converter</a>
{% for p in playlists %}<a href='/stream/{{p}}'>▶ {{p}}</a>{% endfor %}
</body></html>"""
    return render_template_string(html, playlists=PLAYLISTS.keys())

@app.route("/stream/<name>")
def stream_audio(name):
    s = STREAMS_RADIO.get(name)
    if not s: abort(404)
    def gen():
        while True:
            if s["QUEUE"]: yield s["QUEUE"].popleft()
            else: time.sleep(0.1)
    return Response(stream_with_context(gen()), mimetype="audio/mpeg")

# ==============================================================
# 🚀 Start
# ==============================================================

if __name__ == "__main__":
    for pname, url in PLAYLISTS.items():
        STREAMS_RADIO[pname] = {"IDS": load_playlist_ids_radio(pname, url), "INDEX": 0, "QUEUE": deque()}
        threading.Thread(target=stream_worker_radio, args=(pname,), daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=False)