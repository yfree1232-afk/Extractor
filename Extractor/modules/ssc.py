import os
import re
import logging
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from Extractor import app
from config import BOT_TEXT

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_. ')
    return name if name else "Unknown_Course"

async def fetch_json_post(session, url, data=None, headers=None, json_data=None):
    try:
        kwargs = {"headers": headers, "timeout": 30}
        if json_data is not None:
            kwargs["json"] = json_data
        else:
            kwargs["data"] = data
        async with session.post(url, **kwargs) as resp:
            return await resp.json()
    except Exception as e:
        logging.error(f"Error fetching JSON from {url}: {e}")
    return None

async def fetch_json_get(session, url, headers=None):
    try:
        async with session.get(url, headers=headers, timeout=30) as resp:
            return await resp.json()
    except Exception as e:
        logging.error(f"Error fetching JSON from {url}: {e}")
    return None

async def process_ssc(bot: Client, m: Message, user_id: int):
    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=100, loop=loop)

    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = await m.reply_text("🔄 **Fetching all SSC Pinnacle courses...**")
        api_base = "https://auth.ssccglpinnacle.com/api"
        auth_headers = {"User-Agent": "Mozilla/5.0"}
            
        courses_url = f"{api_base}/courses"
        batches = await fetch_json_get(session, courses_url, headers=auth_headers)
        
        if not batches or not isinstance(batches, list):
            await editable.edit("❌ **Failed to fetch courses!**")
            return

        text = ''
        for cnt, batch in enumerate(batches):
            name = batch.get("courseTitle", "Unknown")
            price = batch.get("price", "Free")
            text += f"{cnt + 1}. {name} - Rs.{price}\n"
            
        course_details_file = f"{user_id}_ssc_courses.txt"
        with open(course_details_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        caption = (
            f"🎓 <b>SSC PINNACLE COURSES</b> 🎓\n\n"
            f"📚 <b>TOTAL COURSES:</b> {len(batches)}\n\n"
            f"<code>╾───• @PRO_TXT_EXTRATOR_BOT •───╼</code>\n\n"
            "Send the index number to download course"
        )
        
        await editable.delete()
        msg = await m.reply_document(
            document=course_details_file,
            caption=caption,
            file_name="ssc_courses.txt"
        )
        
        try:
            os.remove(course_details_file)
        except:
            pass
            
        try:
            input_msg3 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
            user_choice = input_msg3.text.strip()
            await input_msg3.delete(True)
        except:
            await msg.edit("❌ <b>Timeout!</b>\n\nYou took too long to respond.")
            return
            
        if not user_choice.isdigit() or not (1 <= int(user_choice) <= len(batches)):
            await msg.edit("❌ <b>Invalid Input!</b>\n\nPlease send a valid index number.")
            return
            
        selected_idx = int(user_choice) - 1
        selected_batch = batches[selected_idx]
        course_id = selected_batch.get("_id")
        batch_title = selected_batch.get("courseTitle", "Unknown Batch")
        clean_batch_name = sanitize_filename(batch_title)
        
        status_msg = await m.reply_text(
            "🔄 <b>Processing Course</b>\n"
            f"└─ Current: <code>{batch_title}</code>\n"
            f"Extracting content directly from SSC Pinnacle..."
        )

        # Extract course chapters
        all_outputs = []
        
        def extract_links(node, current_topic=""):
            if isinstance(node, dict):
                title = node.get("title") or node.get("chapterTitle") or node.get("videoTitle") or node.get("originalname") or node.get("name")
                vid_url = node.get("videoUrl") or node.get("videoLink") or node.get("pdfUrl") or node.get("url") or node.get("path")
                
                if vid_url and isinstance(vid_url, str) and (vid_url.startswith("http") or vid_url.startswith("www")):
                    if not vid_url.startswith("http"):
                        vid_url = "https://" + vid_url
                    safe_title = sanitize_filename(title) if title else "Untitled"
                    all_outputs.append(f"{safe_title}:{vid_url}\n")
                    
                for k, v in node.items():
                    extract_links(v, title if title else current_topic)
                    
            elif isinstance(node, list):
                for item in node:
                    extract_links(item, current_topic)

        vids_url = f"{api_base}/youtubeChapters/course/{course_id}"
        vids_resp = await fetch_json_get(session, vids_url, headers=auth_headers)
        if vids_resp:
            extract_links(vids_resp)
            
        pdfs_url = f"{api_base}/pdfs/course/{course_id}"
        pdfs_resp = await fetch_json_get(session, pdfs_url, headers=auth_headers)
        if pdfs_resp:
            extract_links(pdfs_resp)
        
        if len(all_outputs) == 0:
            await status_msg.edit("❌ No content found for this course. (Or content is locked).")
            return
            
        clean_file_name = f"{user_id}_{clean_batch_name}"
        content = ''.join(all_outputs)
        
        with open(f"{clean_file_name}.txt", 'w', encoding='utf-8') as f:
            f.write(content)
            
        video_count = sum(1 for line in all_outputs if ".pdf" not in line.lower())
        pdf_count = sum(1 for line in all_outputs if ".pdf" in line.lower())
        total_links = video_count + pdf_count
        
        caption = (
            f"🎓 <b>SSC PINNACLE EXTRACTED</b> 🎓\n\n"
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

@app.on_message(filters.command(["ssc"]))
async def ssc_command(client, message):
    try:
        user_id = message.from_user.id
        await process_ssc(client, message, user_id)
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@app.on_callback_query(filters.regex("^ssc_$"))
async def ssc_callback(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        await callback_query.answer()
        await process_ssc(client, callback_query.message, user_id)
    except Exception as e:
        try:
            await callback_query.message.reply_text(f"Error: {str(e)}")
        except:
            pass
