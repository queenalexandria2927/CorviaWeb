import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "downloads.log")

def log_download(url, path):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Downloaded from {url} to {path}\n")
    except Exception as e:
        print(f"Error logging download: {e}")
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"Error logging download: {e}\n")                               