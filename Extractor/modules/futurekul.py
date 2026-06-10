import os
import re
import json
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
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

async def get_futurekul_build_id(session):
    try:
        async with session.get("https://www.futurekul.com/", timeout=15) as resp:
            text = await resp.text()
            match = re.search(r'"buildId"\:"(.*?)"', text)
            if match:
                return match.group(1)
    except Exception as e:
        logging.error(f"Error fetching Futurekul build ID: {e}")
    return None

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=60) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logging.error(f"Error fetching JSON from {url}: {e}")
    return None

def clean_html(raw_html):
    if not raw_html:
        return "Untitled"
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

async def process_futurekul(bot: Client, m: Message, user_id: int):
    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=100, loop=loop)

    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = await m.reply_text("Fetching Futurekul courses... Please wait.")
        
        try:
            build_id = await get_futurekul_build_id(session)
            if not build_id:
                await editable.edit("Failed to connect to Futurekul frontend.")
                return
                
            # Fetch ALL active courses from Next.js without needing auth
            courses_url = f"https://www.futurekul.com/_next/data/{build_id}/en-US/courses.json"
            courses_data = await fetch_json(session, courses_url)
            
            if not courses_data or 'pageProps' not in courses_data:
                await editable.edit("Failed to fetch course list.")
                return
                
            batches = courses_data['pageProps'].get('onlineCoursesList', [])
            if not batches:
                await editable.edit("No active courses found on Futurekul.")
                return
                
            text = ''
            for cnt, batch in enumerate(batches):
                name = batch.get("title", "Unknown")
                price = batch.get("price", "Free")
                text += f"{cnt + 1}. {name} - Rs.{price}\n"
                
            course_details_file = f"{user_id}_futurekul_courses.txt"
            with open(course_details_file, 'w', encoding='utf-8') as f:
                f.write(text)
                
            caption = (
                f"🎓 <b>FUTUREKUL COURSES</b> 🎓\n\n"
                f"📚 <b>TOTAL COURSES:</b> {len(batches)}\n\n"
                f"<code>╾───• @PRO_TXT_EXTRATOR_BOT •───╼</code>\n\n"
                "Send the index number to download course"
            )
            
            await editable.delete()
            msg = await m.reply_document(
                document=course_details_file,
                caption=caption,
                file_name="futurekul_courses.txt"
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
            slug = selected_batch.get("slug")
            batch_title = selected_batch.get("title", "Unknown Batch")
            clean_batch_name = sanitize_filename(batch_title)
            
            status_msg = await m.reply_text(
                "🔄 <b>Processing Course</b>\n"
                f"└─ Current: <code>{batch_title}</code>\n"
                f"Extracting content directly from Futurekul..."
            )
            
            # Fetch course detail directly from Next.js payload
            detail_url = f"https://www.futurekul.com/_next/data/{build_id}/en-US/courses/{slug}/{course_id}.json?slug={slug}&id={course_id}"
            detail_data = await fetch_json(session, detail_url)
            
            if not detail_data or 'pageProps' not in detail_data:
                await status_msg.edit(f"❌ <b>Data Error</b>\n\nCould not fetch course details for {batch_title}.")
                return
                
            course_detail = detail_data['pageProps'].get('courseDetail', {})
            all_outputs = []
            
            # 1. Process Paid Classes (Topics & Videos)
            paid_classes = course_detail.get('paid_class', [])
            if isinstance(paid_classes, list):
                for topic in paid_classes:
                    topic_name = topic.get('topic', 'Unknown Topic')
                    classes = topic.get('class', [])
                    if classes:
                        all_outputs.append(f"\n{topic_name}\n\n")
                        for cls in classes:
                            c_name = clean_html(cls.get('class_name', 'Untitled'))
                            c_link = cls.get('link', '')
                            if c_link:
                                all_outputs.append(f"{c_name}:{c_link}\n")

            # 2. Process PDFs
            pdfs = course_detail.get('pdf', [])
            if isinstance(pdfs, list):
                for p_topic in pdfs:
                    topic_name = p_topic.get('topic_name', 'PDFs')
                    pdf_list = p_topic.get('pdf', [])
                    if pdf_list:
                        all_outputs.append(f"\n{topic_name} (PDFs)\n\n")
                        for p in pdf_list:
                            p_name = clean_html(p.get('pdf_name') or p.get('pdf_title') or 'Untitled PDF')
                            p_url = p.get('pdf_url', '')
                            if p_url:
                                if not p_url.startswith('http'):
                                    p_url = f"https://www.futurekul.com/admin/{p_url}"
                                all_outputs.append(f"{p_name}:{p_url}\n")
                                
            # 3. Process Free/Demo Classes (if any)
            for free_key in ['free_class', 'demoVideos', 'freeDemoVideo']:
                free_items = course_detail.get(free_key, [])
                if isinstance(free_items, list) and free_items:
                    valid_items = [i for i in free_items if isinstance(i, dict) and i.get('link')]
                    if valid_items:
                        all_outputs.append(f"\nFree / Demo ({free_key})\n\n")
                        for item in valid_items:
                            c_name = clean_html(item.get('class_name', 'Untitled Demo'))
                            c_link = item.get('link', '')
                            if c_link:
                                all_outputs.append(f"{c_name}:{c_link}\n")

            if len(all_outputs) == 0:
                await status_msg.edit("❌ No content found for this course.")
                return
                
            clean_file_name = f"{user_id}_{clean_batch_name}"
            content = ''.join(all_outputs)
            
            with open(f"{clean_file_name}.txt", 'w', encoding='utf-8') as f:
                f.write(content)
                
            video_count = sum(1 for line in all_outputs if not line.endswith(".pdf\n") and ":" in line and "http" in line and ".pdf" not in line.lower())
            pdf_count = sum(1 for line in all_outputs if ":" in line and ".pdf" in line.lower())
            total_links = video_count + pdf_count
            
            caption = (
                f"🎓 <b>FUTUREKUL EXTRACTED</b> 🎓\n\n"
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

@app.on_callback_query(filters.regex("^futurekul_$"))
async def futurekul_callback(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        await callback_query.answer()
        await process_futurekul(client, callback_query.message, user_id)
    except Exception as e:
        try:
            await callback_query.message.reply_text(f"Error: {str(e)}")
        except:
            pass

