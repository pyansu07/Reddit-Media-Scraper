import os
import time
import requests
import json
import shutil
import sys
import threading
import queue
import random
import subprocess

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
TARGET_SUBREDDIT = "Subreddit_name" 

BASE_DIR = "./reddit_data"
MIN_FREE_GB = 10.0 

NUM_WORKERS = 3
MAX_QUEUE_SIZE = 100
USE_ARIA2 = False

HISTORY_FILE = os.path.join(BASE_DIR, "history_MASTER.txt") 
CHECKPOINT_FILE = f"checkpoint_{TARGET_SUBREDDIT}.json"

SEARCH_QUERIES = [
    "Sora", "Kling", "Luma", "Dream Machine", "Runway Gen-3", "Pika Labs", 
    "Midjourney", "Stable Diffusion", "SDXL", "Flux.1", "DALL-E 3", 
    "Leonardo AI", "Udio", "Suno", "Haiper", "Vidu", "Hedra", "LivePortrait",
    "photorealistic", "cinematic", "unreal engine", "octane render", "8k", 
    "masterpiece", "high resolution", "hyperrealistic", "volumetric lighting",
    "workflow", "comfyui", "automatic1111", "lora", "checkpoint", 
    "slow motion", "panning", "drone shot", "timelapse", "morphing", 
    "cyberpunk", "surreal", "fantasy", "steampunk", "anime style", "waifu",
    "q", "z", "x", "j", "v", "k"
]

SORT_MODES = ["new", "relevance", "top"]

FLAIR_MAP = {
    "kling": "kling", "runway": "runway", "pika": "pika", "sora": "sora",
    "midjourney": "midjourney", "stable diffusion": "stable-diffusion", "sd": "stable-diffusion",
    "flux": "flux", "dalle": "dall-e", "anime": "anime-models", "leonardo": "leonardo", 
    "dreambooth": "dreambooth", "luma": "luma-dream-machine"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

print_lock = threading.Lock()

# ==========================================
# 🚦 HARD REDDIT RATE LIMIT (≈70 RPM)
# ==========================================
SAFE_RPM = 70
BASE_DELAY = 60 / SAFE_RPM       # ≈0.85s
JITTER = (0.15, 0.45)
MAX_BACKOFF = 60.0
_initial_backoff = 2.0

# global rate control
rate_lock = threading.Lock()
last_request_time = 0
backoff_until = 0
_backoff = _initial_backoff

# ==========================================
# 🔗 REDDIT GET WITH THREAD-SAFE 429 HANDLING
# ==========================================
def reddit_get(url, headers):
    global last_request_time, backoff_until, _backoff

    while True:
        with rate_lock:
            now = time.time()
            # wait if global backoff is active
            if now < backoff_until:
                wait = backoff_until - now
                safe_print(f"⏳ Waiting for global backoff {wait:.1f}s")
                time.sleep(wait)

            # enforce BASE_DELAY between requests
            delta = now - last_request_time
            if delta < BASE_DELAY:
                time.sleep(BASE_DELAY - delta)

            # add jitter
            time.sleep(random.uniform(*JITTER))
            last_request_time = time.time()

        try:
            r = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            safe_print(f"⚠️ Request error: {e}")
            time.sleep(3)
            continue

        if r.status_code in (403, 429):
            retry = int(r.headers.get("Retry-After", 30))
            with rate_lock:
                backoff_until = time.time() + retry + random.uniform(5, 10)
            safe_print(f"🚫 {r.status_code} hit → backing off {retry}s, exponential {_backoff:.1f}s")
            time.sleep(_backoff)
            _backoff = min(_backoff * 2, MAX_BACKOFF)
            continue

        # success → reset exponential backoff
        _backoff = _initial_backoff
        return r

# ==========================================
# 🛡️ HISTORY
# ==========================================
def load_global_history():
    if not os.path.exists(HISTORY_FILE): return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except:
        return set()

def append_to_global_history(post_id):
    for _ in range(10):
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(f"{post_id}\n")
            return True
        except PermissionError:
            time.sleep(random.uniform(0.1, 0.4))
    return False

# ==========================================
# 🛠️ HELPERS
# ==========================================
def safe_print(msg):
    with print_lock:
        print(msg)

def check_disk_space():
    try:
        total, used, free = shutil.disk_usage(BASE_DIR)
        return (free / (1024**3)) > MIN_FREE_GB
    except:
        return True

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"query_idx": 0, "sort_idx": 0}

def save_checkpoint(q_idx, s_idx):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"query_idx": q_idx, "sort_idx": s_idx}, f)

def detect_label(flair, title):
    combined = (str(flair) + " " + str(title)).lower()
    for key, label in FLAIR_MAP.items():
        if key in combined:
            return label
    return "misc"

# ==========================================
# 📥 DOWNLOAD WORKER
# ==========================================
def download_task(task_queue, local_history_cache):
    while True:
        task = task_queue.get()
        if task is None:
            break

        url, folder, filename, pid, is_video = task

        if pid in load_global_history():
            task_queue.task_done()
            continue

        success = False
        name_no_ext = os.path.splitext(filename)[0]

        if is_video:
            cmd = [
                "python", "-m", "yt_dlp",
                "--quiet", "--ignore-errors",
                "--max-filesize", "100M",
                "--user-agent", USER_AGENT,
                "-o", f"{folder}/{name_no_ext}.%(ext)s",
                url
            ]
            try:
                subprocess.run(cmd, timeout=45)
                success = True
            except:
                pass
        else:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code == 200:
                    with open(os.path.join(folder, filename), "wb") as f:
                        f.write(r.content)
                    success = True
            except:
                pass

        if success:
            if append_to_global_history(pid):
                local_history_cache.add(pid)
                safe_print(f"   ✅ [{TARGET_SUBREDDIT}] Saved {filename}")

        task_queue.task_done()

# ==========================================
# 🚀 MAIN
# ==========================================
if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)

    local_history = load_global_history()
    queued_ids = set()
    cp = load_checkpoint()

    q = queue.Queue(maxsize=MAX_QUEUE_SIZE)

    for label in list(set(FLAIR_MAP.values())) + ["misc"]:
        os.makedirs(os.path.join(BASE_DIR, label, "video"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, label, "photo"), exist_ok=True)

    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=download_task, args=(q, local_history), daemon=True)
        t.start()

    for q_idx in range(cp["query_idx"], len(SEARCH_QUERIES)):
        query = SEARCH_QUERIES[q_idx]
        for sort_mode in SORT_MODES:
            safe_print(f"\n🔎 [{TARGET_SUBREDDIT}] {query} ({sort_mode})")

            after = None
            for _ in range(5):
                search_url = f"https://www.reddit.com/r/{TARGET_SUBREDDIT}/search.json?q={query}&restrict_sr=1&sort={sort_mode}&limit=100"
                if after:
                    search_url += f"&after={after}"

                resp = reddit_get(search_url, HEADERS)
                if resp.status_code != 200:
                    break

                data = resp.json().get("data", {})
                children = data.get("children", [])
                after = data.get("after")

                for child in children:
                    post = child["data"]
                    pid = post["id"]
                    if pid in local_history or pid in queued_ids:
                        continue

                    label = detect_label(post.get("link_flair_text"), post.get("title"))
                    d_url = post.get("url_overridden_by_dest", post.get("url"))
                    is_vid = post.get("is_video", False)
                    permalink = f"https://www.reddit.com{post['permalink']}"

                    if is_vid or "v.redd.it" in d_url:
                        q.put((permalink, os.path.join(BASE_DIR, label, "video"), f"{pid}.mp4", pid, True))
                        queued_ids.add(pid)
                    elif d_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        ext = os.path.splitext(d_url)[1]
                        q.put((d_url, os.path.join(BASE_DIR, label, "photo"), f"{pid}{ext}", pid, False))
                        queued_ids.add(pid)

                if not after:
                    break

            save_checkpoint(q_idx, 0)

    q.join()
    print("✅ DONE")
