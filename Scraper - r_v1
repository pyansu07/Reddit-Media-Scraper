import os
import time
import requests
import json
import shutil
import sys

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# CHANGE THIS TO THE SUB YOU WANT TO SCRAPE NOW
TARGET_SUBREDDIT = "SUBREDDIT_NAME" 

BASE_DIR = "./reddit_data"
MIN_FREE_GB = 10.0 

# The "Ultimate AI Harvest" List
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

SORT_MODES = ["relevance", "top", "new"]

FLAIR_MAP = {
    "kling": "kling", "runway": "runway", "pika": "pika", "sora": "sora",
    "midjourney": "midjourney", "stable diffusion": "stable-diffusion", "sd": "stable-diffusion",
    "flux": "flux", "dalle": "dall-e", "anime": "anime-models", "leonardo": "leonardo", 
    "dreambooth": "dreambooth", "luma": "luma-dream-machine"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}
HISTORY_FILE = "history.txt"
CHECKPOINT_FILE = "checkpoint.json"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def check_disk_space():
    total, used, free = shutil.disk_usage(BASE_DIR)
    free_gb = free / (1024**3)
    return free_gb > MIN_FREE_GB, free_gb

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f: 
        return set(line.strip() for line in f)

def save_to_history(post_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(f"{post_id}\n")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f: return json.load(f)
    return {"subreddit": "", "query_idx": 0, "sort_idx": 0}

def save_checkpoint(query_idx, sort_idx):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"subreddit": TARGET_SUBREDDIT, "query_idx": query_idx, "sort_idx": sort_idx}, f)

def detect_label(flair, title):
    combined = (str(flair) + " " + str(title)).lower()
    for key, label in FLAIR_MAP.items():
        if key in combined: return label
    return "misc"

def download_video(url, folder, filename):
    name_no_ext = os.path.splitext(filename)[0]
    # Restricting to high quality but keeping it under 100MB to save space
    cmd = (f'python -m yt_dlp --quiet --no-warnings --max-filesize 100M '
           f'--user-agent "{USER_AGENT}" -o "{folder}/{name_no_ext}.%(ext)s" "{url}"')
    return os.system(cmd) == 0

def download_image(url, folder, filename):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            with open(os.path.join(folder, filename), "wb") as f: f.write(r.content)
            return True
    except: return False
    return False

# ==========================================
# MAIN PROCESS
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)
    
    history = load_history()
    cp = load_checkpoint()
    
    # If we are starting a NEW subreddit, reset the checkpoint
    if cp["subreddit"] != TARGET_SUBREDDIT:
        cp = {"subreddit": TARGET_SUBREDDIT, "query_idx": 0, "sort_idx": 0}

    print(f"🚀 HARVESTING: r/{TARGET_SUBREDDIT}")
    print(f"📈 Resuming from Query #{cp['query_idx']} ({SEARCH_QUERIES[cp['query_idx']]})")

    # Create sub-folders
    for label in list(set(FLAIR_MAP.values())) + ["misc"]:
        os.makedirs(os.path.join(BASE_DIR, label, "video"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, label, "photo"), exist_ok=True)

    # LOOP QUERIES
    for q_idx in range(cp["query_idx"], len(SEARCH_QUERIES)):
        query = SEARCH_QUERIES[q_idx]
        
        # LOOP SORTS
        start_s_idx = cp["sort_idx"] if q_idx == cp["query_idx"] else 0
        for s_idx in range(start_s_idx, len(SORT_MODES)):
            sort_mode = SORT_MODES[s_idx]
            
            # Disk Check
            has_space, free_gb = check_disk_space()
            if not has_space:
                print(f"🛑 DISK FULL ({free_gb:.2f}GB left). Upload and clear folder!")
                sys.exit()

            print(f"\n🔎 Query: '{query}' | Sort: {sort_mode}")
            
            after = None
            for page in range(10): # Deep search (1000 posts per query/sort)
                try:
                    # Filter for media sites to ensure we only get generated files
                    search_url = f"https://www.reddit.com/r/{TARGET_SUBREDDIT}/search.json?q={query}+(site:v.redd.it+OR+site:i.redd.it+OR+site:imgur.com)&restrict_sr=1&sort={sort_mode}&limit=100"
                    if after: search_url += f"&after={after}"
                    
                    resp = requests.get(search_url, headers=HEADERS)
                    if resp.status_code != 200: break
                    
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    if not children: break
                    after = data.get("data", {}).get("after")

                    for child in children:
                        post = child["data"]
                        pid = post["id"]
                        
                        if pid in history: continue

                        label = detect_label(post.get("link_flair_text"), post.get("title"))
                        d_url = post.get("url_overridden_by_dest", post.get("url"))
                        is_vid = post.get("is_video", False)
                        success = False

                        if is_vid or "v.redd.it" in d_url or "youtu" in d_url:
                            print(f"   🎬 [{label}] {pid}")
                            if download_video(f"https://www.reddit.com{post['permalink']}" if is_vid else d_url, 
                                              os.path.join(BASE_DIR, label, "video"), f"{pid}.mp4"):
                                success = True
                        
                        elif d_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            print(f"   📸 [{label}] {pid}")
                            ext = os.path.splitext(d_url)[1] or ".jpg"
                            if download_image(d_url, os.path.join(BASE_DIR, label, "photo"), f"{pid}{ext}"):
                                success = True

                        if success:
                            save_to_history(pid)
                            history.add(pid)
                            if not check_disk_space()[0]: sys.exit()

                    time.sleep(1.5) # Anti-ban delay
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
                    break
                if not after: break
            
            save_checkpoint(q_idx, s_idx) # Save progress after every sort-mode finishes
        
    print(f"\n✅ FINISHED r/{TARGET_SUBREDDIT}. Change TARGET_SUBREDDIT for the next one!")
