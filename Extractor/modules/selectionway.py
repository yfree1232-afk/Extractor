import os
import re
import time
import json
import logging
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from Extractor import app
from config import PREMIUM_LOGS, BOT_TEXT

API_BASE = "https://gdgoenkaratia.com/api"
USER_ID_PARAM = ""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.selectionway.com/",
    "Origin": "https://www.selectionway.com",
}

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_. ')
    return name if name else "Unknown_Batch"

async def fetch_json(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=60) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
    return None

async def process_selectionwaywp(bot: Client, m: Message, user_id: int):
    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=100, loop=loop)

    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = await m.reply_text("Fetching Selection Way courses...")
        
        try:
            url = f"{API_BASE}/courses/active?userId={USER_ID_PARAM}"
            data = await fetch_json(session, url)
            
            if not data or data.get("state") != 200:
                await editable.edit("Failed to fetch courses or API error.")
                return
                
            batches = data.get("data", [])
            if not batches:
                await editable.edit("No active batches found.")
                return
                
            text = ''
            for cnt, batch in enumerate(batches):
                name = batch.get("title", "Unknown")
                price = batch.get("price", "Free")
                text += f"{cnt + 1}. {name} - Rs.{price}\n"
                
            course_details_file = f"{user_id}_selectionway_courses.txt"
            with open(course_details_file, 'w', encoding='utf-8') as f:
                f.write(text)
                
            caption = (
                f"🎓 <b>SELECTION WAY COURSES</b> 🎓\n\n"
                f"📚 <b>TOTAL COURSES:</b> {len(batches)}\n\n"
                f"<code>╾───• @PRO_TXT_EXTRATOR_BOT •───╼</code>\n\n"
                "Send the index number to download course"
            )
            
            await editable.delete()
            msg = await m.reply_document(
                document=course_details_file,
                caption=caption,
                file_name="selectionway_courses.txt"
            )
            
            try:
                os.remove(course_details_file)
            except:
                pass
                
            try:
                input_msg = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                user_choice = input_msg.text.strip()
                await input_msg.delete(True)
            except:
                await msg.edit("❌ <b>Timeout!</b>\n\nYou took too long to respond.")
                return
                
            if not user_choice.isdigit() or not (1 <= int(user_choice) <= len(batches)):
                await msg.edit("❌ <b>Invalid Input!</b>\n\nPlease send a valid index number.")
                return
                
            selected_idx = int(user_choice) - 1
            selected_batch = batches[selected_idx]
            course_id = selected_batch.get("id")
            batch_title = selected_batch.get("title", "Unknown Batch")
            clean_batch_name = sanitize_filename(batch_title)
            
            status_msg = await m.reply_text(
                "🔄 <b>Processing Course</b>\n"
                f"└─ Current: <code>{batch_title}</code>"
            )
            
            # Fetch topics
            topics_url = f"{API_BASE}/topic-and-section?courseId={course_id}&userId={USER_ID_PARAM}"
            topics_data = await fetch_json(session, topics_url)
            topics = topics_data.get("data", {}).get("topics", []) if topics_data and topics_data.get("state") == 200 else []
            
            if not topics:
                await status_msg.edit("❌ No topics found for this batch.")
                return
                
            all_outputs = []
            
            for topic in topics:
                topic_id = topic.get("topicId")
                topic_name = topic.get("topicName", "Unknown Topic")
                all_outputs.append(f"\n{topic_name}\n\n")
                
                classes_url = f"{API_BASE}/topics/{topic_id}/classes?courseId={course_id}&userId={USER_ID_PARAM}"
                classes_data = await fetch_json(session, classes_url)
                classes = classes_data.get("data", {}).get("classes", []) if classes_data and classes_data.get("state") == 200 else []
                
                for cls in classes:
                    title = cls.get("title", "Untitled")
                    
                    hls_link = cls.get("class_link", "")
                    if hls_link:
                        all_outputs.append(f"{title}:{hls_link}\n")
                        
                    mp4s = cls.get("mp4Recordings", [])
                    if mp4s:
                        for mp4 in mp4s:
                            url = mp4.get("url", "")
                            if url:
                                all_outputs.append(f"{title}:{url}\n")
                                
                    pdfs = cls.get("classPdf", [])
                    if pdfs:
                        for pdf in pdfs:
                            pdf_url = pdf.get("url", "")
                            if pdf_url:
                                all_outputs.append(f"{title} PDF:{pdf_url}\n")
                                
            if not all_outputs:
                await status_msg.edit("❌ No videos or PDFs found in this batch.")
                return
                
            # Save and send
            clean_file_name = f"{user_id}_{clean_batch_name}"
            content = ''.join(all_outputs)
            
            with open(f"{clean_file_name}.txt", 'w', encoding='utf-8') as f:
                f.write(content)
                
            video_count = sum(1 for line in all_outputs if not line.endswith(".pdf\\n") and "PDF:" not in line and ":" in line)
            pdf_count = sum(1 for line in all_outputs if "PDF:" in line)
            total_links = video_count + pdf_count
            
            caption = (
                f"🎓 <b>SELECTION WAY EXTRACTED</b> 🎓\n\n"
                f"📚 <b>BATCH:</b> {batch_title}\n\n"
                f"📊 <b>CONTENT STATS</b>\n"
                f"├─ 📁 Total Links: {total_links}\n"
                f"├─ 🎬 Videos: {video_count}\n"
                f"└─ 📄 PDFs: {pdf_count}\n\n"
                f"🚀 <b>Extracted by</b>: @{(await app.get_me()).username}\n\n"
                f"<code>╾───• {BOT_TEXT} •───╼</code>"
            )
            
            with open(f"{clean_file_name}.txt", 'rb') as f:
                await msg.delete()
                await status_msg.delete()
                await m.reply_document(
                    document=f,
                    caption=caption,
                    file_name=f"{clean_batch_name}.txt"
                )
                
            try:
                os.remove(f"{clean_file_name}.txt")
            except:
                pass
                
        except Exception as e:
            await m.reply_text(f"Error: {str(e)}")
            
        finally:
            await session.close()
            await CONNECTOR.close()

@app.on_callback_query(filters.regex("^selectionwaywp$"))
async def selectionwaywp_callback(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        await callback_query.answer()
        await process_selectionwaywp(client, callback_query.message, user_id)
    except Exception as e:
        try:
            await callback_query.message.reply_text(f"Error: {str(e)}")
        except:
            pass
