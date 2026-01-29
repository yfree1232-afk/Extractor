#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import subprocess
import sys

def run_app():
    try:
        # This assumes you have an app.py in your project root.
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Web app process error: {e}")
        sys.exit(1)

def run_bot():
    try:
        # Ensure sessions directory exists
        os.makedirs("sessions", exist_ok=True)
        
        # Launch the pyrogram/pyromod bot
        subprocess.run([sys.executable, "-m", "Extractor"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Bot process error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in bot process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 1) Load .env locally; on Heroku this is a no-op since env vars are already set
    load_dotenv()

    # 2) Verify we have the creds we need
    from config import API_ID, API_HASH, BOT_TOKEN
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        sys.exit("⚠️  Missing API_ID, API_HASH, or BOT_TOKEN in the environment")

    # 3) Check if running on Heroku
    if os.environ.get('DYNO'):
        # On Heroku, just run the bot
        run_bot()
    else:
        # Locally, run both processes
        import multiprocessing
        procs = [
            multiprocessing.Process(target=run_app, name="web_app"),
            multiprocessing.Process(target=run_bot, name="telegram_bot"),
        ]
        for p in procs:
            p.start()

        # Wait for them (if one dies, we'll exit too)
        for p in procs:
            p.join()
