import os
import io
import re
import time
import random
import json
import threading
import subprocess
import logging
import pandas as pd
from collections import deque
from logging.handlers import RotatingFileHandler
from flask import Flask, request, send_file, Response, render_template_string, abort, stream_with_context

# ==============================================================
# 🧠 Basic Config
# ==============================================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==============================================================
# 📘 MCQ Converter SECTION
# ==============================================================

def parse_mcqs(text):
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
        # ✅ Match option lines
        m_opt = re.match(r'^[\(\[]?([a-dA-D])[\)\:\-]*\s*(.*)', line)
        if m_opt and not capturing_expl:
            opt_text = m_opt.group(2).strip()
            opt_text = re.sub(r'^[\.\)\:\-\s]+', '', opt_text)
            opts[m_opt.group(1).lower()] = opt_text
            continue

        # ✅ Match answer lines
        m_ans = re.match(r'^(\d+)\.\s*(?:Answer|Ans)?[:\-]?\s*([A-Da-d])$', line)
        if m_ans:
            answer = m_ans.group(2).upper()
            qno = m_ans.group(1)
            capturing_expl = True
            explanation_lines = []
            continue

        # ✅ Explanation mode
        if capturing_expl:
            if re.match(r'^\d+\.', line):
                if opts and answer:
                    question_full = '\n'.join(qtext_lines).strip() + '\n' + \
                        f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
                    rows.append([
                        qno,
                        question_full,
                        'A','B','C','D',
                        {"A":1,"B":2,"C":3,"D":4}[answer],
                        ' '.join(explanation_lines).strip(),
                        ""
                    ])
                qno = None
                qtext_lines = []
                opts = {}
                answer = None
                capturing_expl = False
                m_q = re.match(r'^(\d+)\.(.*)', line)
                if m_q:
                    qno = m_q.group(1)
                    qtext_lines = [m_q.group(2).strip()]
                continue
            else:
                explanation_lines.append(line)
                continue

        # ✅ Question start
        m_q = re.match(r'^(\d+)\.(.*)', line)
        if m_q:
            qno = m_q.group(1)
            qtext_lines = [m_q.group(2).strip()]
            continue

        if qno:
            qtext_lines.append(line)

    # ✅ Final flush
    if opts and answer:
        question_full = '\n'.join(qtext_lines).strip() + '\n' + \
            f"A) {opts.get('a','')}\nB) {opts.get('b','')}\nC) {opts.get('c','')}\nD) {opts.get('d','')}"
        rows.append([
            qno,
            question_full,
            'A','B','C','D',
            {"A":1,"B":2,"C":3,"D":4}[answer],
            ' '.join(explanation_lines).strip(),
            ""
        ])

    return rows


@app.route("/mcq", methods=["GET"])
def index_mcq():
    return """
    <!DOCTYPE html>
    <html>
    <head>
    <title>MCQ Converter</title>
    <style>
    body {display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;background:linear-gradient(135deg,#4facfe,#00f2fe);margin:0;}
    .container{text-align:center;background:white;padding:40px;border-radius:15px;box-shadow:0 10px 25px rgba(0,0,0,0.25);width:80%;max-width:900px;}
    h1{font-size:36px;margin-bottom:20px;color:#222;}
    textarea{width:100%;height:400px;padding:15px;font-size:16px;border-radius:10px;border:1px solid #ccc;resize:vertical;margin-bottom:20px;}
    input[type=submit]{margin-top:20px;background:#007bff;color:white;border:none;padding:15px 30px;font-size:18px;border-radius:10px;cursor:pointer;transition:0.3s;}
    input[type=submit]:hover{background:#0056b3;}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>📘 MCQ to Excel Converter</h1>
        <form method="post" action="/convert">
            <textarea name="mcq_text" placeholder="Paste your MCQs here..."></textarea><br>
            <input type="submit" value="Convert to Excel">
        </form>
    </div>
    </body>
    </html>
    """


@app.route('/convert', methods=['POST'])
def convert():
    text = request.form.get("mcq_text", "").strip()
    if not text:
        return "No text provided!", 400

    rows = parse_mcqs(text)
    if not rows:
        return "Could not parse any MCQs. Please check format.", 400

    df = pd.DataFrame(rows, columns=[
        "Sr. No.","Question Text","Option 1","Option 2","Option 3","Option 4",
        "Correct Option Number (1–4)","Explanation","Image URL"
    ])
    output = io.BytesIO()
    df.to_excel(output, index=False, header=True)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="mcqs.xlsx")

# ==============================================================
# 🎶 YouTube Playlist Radio SECTION
# ==============================================================

LOG_PATH = "/mnt/data/radio.log"
COOKIES_PATH = "/mnt/data/cookies.txt"
CACHE_FILE = "/mnt/data/playlist_cache.json"
# Ensure paths exist (will create directories if necessary)
os.makedirs(DOWNLOAD_DIR := "/mnt/data/radio_cache", exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

handler = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024, backupCount=3)
logging.getLogger().addHandler(handler)

PLAYLISTS = {
    "kas_ranker": "https://youtube.com/playlist?list=PLS2N6hORhZbvjEB9VUAtuvPkirvoKqzfn",
    "ca": "https://youtube.com/playlist?list=PLYKzjRvMAyci_W5xYyIXHBoR63eefUadL",
    "talent_ca": "https://youtube.com/playlist?list=PL5RD_h4gTSuQbCndwvolzeTDwZVGwCl53",
}

PLAY_MODES = {
    # e.g. "kas_ranker": "shuffle", "ca": "reverse"
}

STREAMS_RADIO = {}
MAX_QUEUE = 64
REFRESH_INTERVAL = 600  # 10 min refresh loop interval (used by cache_refresher)

# ==============================================================
# 🧩 Playlist Caching + Loader
# ==============================================================

def load_cache_radio():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE))
        except Exception:
            return {}
    return {}

def save_cache_radio(data):
    try:
        json.dump(data, open(CACHE_FILE, "w"))
    except Exception as e:
        logging.error(e)

CACHE_RADIO = load_cache_radio()

def get_playlist_ids(url):
    """Return list of YouTube video IDs from a playlist URL sorted by latest upload date."""
    try:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--quiet",
            url
        ]
        # If yt-dlp isn't present this will raise FileNotFoundError
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        entries = [e for e in data.get("entries", []) if "id" in e]
        # Sort by upload date descending (latest first)
        entries.sort(key=lambda e: e.get("upload_date", ""), reverse=True)
        return [entry["id"] for entry in entries]
    except FileNotFoundError:
        logging.error("yt-dlp not found. Install yt-dlp or ensure it is on PATH.")
        return []
    except subprocess.CalledProcessError as e:
        logging.error(f"yt-dlp call failed: {e}; stdout: {e.stdout}; stderr: {e.stderr}")
        return []
    except Exception as e:
        logging.exception(f"get_playlist_ids() failed for {url}: {e}")
        return []

def load_playlist_ids_radio(name, url):
    """Load and cache YouTube playlist IDs with safe mode handling."""
    try:
        ids = get_playlist_ids(url)
        if not ids:
            logging.warning(f"[{name}] ⚠️ No videos found in playlist — using empty list.")
            CACHE_RADIO[name] = []
            save_cache_radio(CACHE_RADIO)
            return []

        mode = PLAY_MODES.get(name, "normal")
        mode = (mode or "normal").lower().strip()
        if mode == "shuffle":
            random.shuffle(ids)
        elif mode == "reverse":
            ids.reverse()

        CACHE_RADIO[name] = ids
        save_cache_radio(CACHE_RADIO)
        logging.info(f"[{name}] Cached {len(ids)} videos in {mode.upper()} mode.")
        return ids

    except Exception as e:
        logging.exception(f"[{name}] ❌ Failed to load playlist ({e}) — fallback to cached ids.")
        return CACHE_RADIO.get(name, [])

# ==============================================================
# ⚡ Robust stream worker (single definition)
# ==============================================================

def stream_worker_radio(name):
    """
    Worker for a single playlist:
    - Loads playlist IDs when needed
    - Uses yt-dlp -> ffmpeg pipe to produce mp3 chunks
    - Pushes small chunks to STREAMS_RADIO[name]['QUEUE']
    """
    s = STREAMS_RADIO[name]
    while True:
        ytdlp = None
        ffmpeg = None
        try:
            ids = s.get("IDS") or []
            if not ids:
                ids = load_playlist_ids_radio(name, PLAYLISTS[name])
                s["IDS"] = ids

            if not ids:
                logging.warning(f"[{name}] No playlist ids found; sleeping 60s...")
                time.sleep(60)
                continue

            vid = ids[s["INDEX"] % len(ids)]
            s["INDEX"] += 1
            url = f"https://www.youtube.com/watch?v={vid}"
            logging.info(f"[{name}] ▶️ Now playing: {url}")

            # Build yt-dlp command; include cookies only if file exists
            ytdlp_cmd = [
                "yt-dlp", "-f", "bestaudio/best",
                "--no-warnings", "--quiet",
                "-o", "-", url
            ]
            if os.path.exists(COOKIES_PATH):
                # Insert cookies options before url
                # We insert just before the last element (the url)
                ytdlp_cmd.insert(-1, COOKIES_PATH)
                ytdlp_cmd.insert(-1, "--cookies")
                logging.debug(f"[{name}] Using cookies file at {COOKIES_PATH}")
            else:
                logging.debug(f"[{name}] Cookies file not found at {COOKIES_PATH}; running without cookies.")

            # Launch processes
            try:
                ytdlp = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            except FileNotFoundError:
                logging.error(f"[{name}] yt-dlp binary not found. Ensure yt-dlp is installed and on PATH.")
                time.sleep(10)
                continue

            ffmpeg_cmd = [
                "ffmpeg", "-loglevel", "error", "-i", "pipe:0",
                "-ac", "1", "-ar", "22050", "-b:a", "40k", "-f", "mp3", "pipe:1"
            ]
            try:
                ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=ytdlp.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            except FileNotFoundError:
                logging.error(f"[{name}] ffmpeg binary not found. Ensure ffmpeg is installed and on PATH.")
                # make sure to kill ytdlp if it was started
                try:
                    if ytdlp and ytdlp.poll() is None:
                        ytdlp.kill()
                except Exception:
                    pass
                time.sleep(10)
                continue

            # Allow yt-dlp to exit when ffmpeg closes
            if ytdlp and ytdlp.stdout:
                try:
                    ytdlp.stdout.close()
                except Exception:
                    pass

            # Read ffmpeg stdout and push to queue
            while True:
                chunk = None
                try:
                    chunk = ffmpeg.stdout.read(2048)
                except Exception as e:
                    logging.debug(f"[{name}] ffmpeg stdout read error: {e}")
                    break

                if not chunk:
                    # no more data from ffmpeg for this track
                    break

                # backpressure: keep queue under MAX_QUEUE
                while len(s["QUEUE"]) >= MAX_QUEUE:
                    time.sleep(0.05)

                s["QUEUE"].append(chunk)

            # Wait (short) for processes to exit gracefully
            try:
                ffmpeg.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.debug(f"[{name}] ffmpeg did not exit quickly, continuing.")

            try:
                if ytdlp:
                    ytdlp.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logging.debug(f"[{name}] ytdlp did not exit quickly.")

            logging.info(f"[{name}] ✅ Finished track {vid}")
            time.sleep(1)

        except subprocess.TimeoutExpired:
            logging.warning(f"[{name}] Worker timeout while waiting for processes — attempting cleanup.")
            # kill if exist
            try:
                if ffmpeg and ffmpeg.poll() is None:
                    ffmpeg.kill()
            except Exception:
                pass
            try:
                if ytdlp and ytdlp.poll() is None:
                    ytdlp.kill()
            except Exception:
                pass
            time.sleep(3)
        except Exception as e:
            logging.exception(f"[{name}] Worker error: {e}")
            # ensure processes are killed if something bad happened
            try:
                if ffmpeg and ffmpeg.poll() is None:
                    ffmpeg.kill()
            except Exception:
                pass
            try:
                if ytdlp and ytdlp.poll() is None:
                    ytdlp.kill()
            except Exception:
                pass
            time.sleep(5)
        finally:
            # best-effort cleanup
            try:
                if ffmpeg and ffmpeg.poll() is None:
                    ffmpeg.kill()
            except Exception:
                pass
            try:
                if ytdlp and ytdlp.poll() is None:
                    ytdlp.kill()
            except Exception:
                pass

# ==============================================================
# 🌐 Flask Routes
# ==============================================================

@app.route("/")
def home():
    playlists = list(PLAYLISTS.keys())
    html = """<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🎧 YouTube Radio</title>
<style>
body{background:#000;color:#0f0;font-family:Arial,Helvetica,sans-serif;text-align:center;margin:0;padding:12px}
a{display:block;color:#0f0;text-decoration:none;border:1px solid #0f0;padding:10px;margin:8px;border-radius:8px;font-size:18px}
a:hover{background:#0f0;color:#000}
</style></head><body>
<h2>🎶 YouTube Playlist Radio</h2>
<a href="/mcq">🧠 Go to MCQ Converter</a>
{% for p in playlists %}
  <a href="/stream/{{p}}">▶ {{p|capitalize}}</a>
{% endfor %}
</body></html>"""
    return render_template_string(html, playlists=playlists)

@app.route("/health")
def health():
    return {"status": "ok", "playlists": list(PLAYLISTS.keys())}

@app.route("/listen/<name>")
def listen_radio_download(name):
    if name not in STREAMS_RADIO:
        abort(404)
    s = STREAMS_RADIO[name]
    def gen():
        while True:
            if s["QUEUE"]:
                yield s["QUEUE"].popleft()
            else:
                time.sleep(0.05)
    headers = {"Content-Disposition": f"attachment; filename={name}.mp3"}
    return Response(stream_with_context(gen()), mimetype="audio/mpeg", headers=headers)

# --- REVISED stream route (play inline, no attachment) ---
@app.route("/stream/<name>")
def stream_audio(name):
    if name not in STREAMS_RADIO:
        abort(404)
    s = STREAMS_RADIO[name]

    def gen():
        try:
            while True:
                if s["QUEUE"]:
                    # yield next chunk (deque left-pop)
                    chunk = s["QUEUE"].popleft()
                    if chunk:
                        yield chunk
                    else:
                        # avoid busy-loop on empty/zero bytes
                        time.sleep(0.01)
                else:
                    time.sleep(0.02)
        except GeneratorExit:
            logging.info(f"[{name}] Client disconnected from stream.")
        except Exception as e:
            logging.exception(f"[{name}] Stream generator error: {e}")

    # Serve as playable audio (no 'attachment' header)
    headers = {
        "Cache-Control": "no-cache, no-transform",
        # Note: do NOT set Content-Length for continuous streams
    }
    return Response(stream_with_context(gen()), mimetype="audio/mpeg", headers=headers)

# ==============================================================
# 🔁 Cache refresher
# ==============================================================

def cache_refresher():
    """Periodically refresh playlist caches for all playlists."""
    while True:
        for name, url in PLAYLISTS.items():
            try:
                last = STREAMS_RADIO.get(name, {}).get("LAST_REFRESH", 0)
                # refresh every 2 hours (7200s)
                if time.time() - last > 7200:
                    logging.info(f"[{name}] 🔁 Refreshing playlist cache...")
                    new_ids = load_playlist_ids_radio(name, url)
                    if name in STREAMS_RADIO:
                        STREAMS_RADIO[name]["IDS"] = new_ids
                        STREAMS_RADIO[name]["LAST_REFRESH"] = time.time()
                    else:
                        # ensure stream entry exists if missing
                        STREAMS_RADIO[name] = {
                            "IDS": new_ids,
                            "INDEX": 0,
                            "QUEUE": deque(),
                            "LAST_REFRESH": time.time()
                        }
            except Exception as e:
                logging.exception(f"cache_refresher error for {name}: {e}")
        time.sleep(REFRESH_INTERVAL)

# ==============================================================
# 🚀 START SERVER
# ==============================================================

if __name__ == "__main__":
    # sanity check: ensure yt-dlp and ffmpeg exist (warn only)
    for bin_name in ("yt-dlp", "ffmpeg"):
        if not shutil.which(bin_name) if (shutil := __import__("shutil")) else True:
            # the above inline import/shutil.which guarded for readability
            pass  # ignored; we'll handle missing binaries in worker

    # initialize STREAMS_RADIO entries and start workers
    for pname, url in PLAYLISTS.items():
        STREAMS_RADIO[pname] = {
            "IDS": load_playlist_ids_radio(pname, url),
            "INDEX": 0,
            "QUEUE": deque(),
            "LAST_REFRESH": time.time(),
        }
        threading.Thread(target=stream_worker_radio, args=(pname,), daemon=True).start()

    # Start cache refresher thread properly
    threading.Thread(target=cache_refresher, daemon=True).start()

    logging.info("🚀 Unified Flask App (Radio + MCQ Converter) running at http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000)