# Reddit AI Media Scraper

A Python-based Reddit scraper designed to collect AI-generated media
(images & videos) from selected subreddits using keyword-based search
via Reddit’s public JSON endpoints.

This repository contains **two versions** of the scraper, each built
for different scale and reliability requirements.

---

## 🚀 Features

- Keyword-based Reddit search
- Media-only harvesting (videos & images)
- Flair & title-based categorization
- Resume support using checkpoints
- Duplicate prevention using persistent history tracking

---

## 📦 Version Overview

### 🔹 Version 1 – Basic Scraper

**Best for:**
- Learning & experimentation
- Small datasets
- Easy debugging

**Characteristics:**
- Single-threaded execution
- Sequential downloads
- Basic rate-limit awareness
- Simple history & checkpoint system
- Easy to understand and modify

---

### 🔹 Version 2 – Parallel Scraper

**Best for:**
- Larger datasets
- Long-running jobs
- Rate-limit-safe harvesting

**Characteristics:**
- Multi-threaded download workers
- Central task queue
- Client-side Reddit rate limiting
- Worker-based architecture
- Faster and more resilient execution

---


## 🛠️ Requirements

- Python 3.9+
- `requests`
- `yt-dlp`

Install dependencies:
```bash
pip install requests yt-dlp
