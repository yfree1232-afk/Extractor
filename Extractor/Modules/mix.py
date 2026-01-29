import asyncio
import aiohttp
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from pyrogram import filters
import cloudscraper
from Extractor import app
from config import PREMIUM_LOGS, join,BOT_TEXT
import os
import base64
import time
from datetime import datetime
from Extractor.core.utils import forward_to_log
import pytz
import config 
import logging
from bs4 import BeautifulSoup

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

join = config.join
india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")


PREMIUM_LOGS = PREMIUM_LOGS
def decrypt(enc):
    """Decrypt AES encrypted content."""
    try:
        if not enc:
            return ""
        enc = b64decode(enc.split(':')[0])
        key = '638udh3829162018'.encode('utf-8')
        iv = 'fedcba9876543210'.encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(enc), AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""

def decode_base64(encoded_str):
    """Decode base64 encoded string."""
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return ""

async def fetch_item_details(session, api_base, course_id, item, headers):
    """Fetch details for a single item (video/pdf)."""
    try:
        fi = item.get("id")
        vt = item.get("Title", "")
        outputs = []

        async with session.get(
            f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&folder_wise_course=1&ytflag=0&video_id={fi}",
            headers=headers
        ) as response:
            if not response.headers.get('Content-Type', '').startswith('application/json'):
                logger.error(f"Unexpected response type for video ID {fi}")
                return []

            r4 = await response.json()
            data = r4.get("data")
            if not data:
                return []

            vt = data.get("Title", "")
            vl = data.get("download_link", "")

            # Process video link
            if vl:
                dvl = decrypt(vl)
                if dvl:
                    outputs.append(f"{vt}:{dvl}")
            else:
                # Process encrypted links
                for link in data.get("encrypted_links", []):
                    a = link.get("path")
                    k = link.get("key")
                    if a and k:
                        k1 = decrypt(k)
                        k2 = decode_base64(k1)
                        da = decrypt(a)
                        if da and k2:
                            outputs.append(f"{vt}:{da}*{k2}")
                            break
                    elif a:
                        da = decrypt(a)
                        if da:
                            outputs.append(f"{vt}:{da}")
                            break

            # Process additional materials
            if data.get("material_type") == "VIDEO":
                # Process PDF links
                for pdf_num in range(1, 3):
                    pdf_link = data.get(f"pdf_link{'' if pdf_num == 1 else str(pdf_num)}", "")
                    pdf_key = data.get(f"pdf{'_' if pdf_num == 1 else str(pdf_num)}_encryption_key", "")
                    
                    if pdf_link and pdf_key:
                        dp = decrypt(pdf_link)
                        dpk = decrypt(pdf_key)
                        if dp:
                            if dpk == "abcdefg":
                                outputs.append(f"{vt}:{dp}")
                            else:
                                outputs.append(f"{vt}:{dp}*{dpk}")

        return outputs

    except Exception as e:
        logger.error(f"Error fetching item details: {e}")
        return []

async def fetch_folder_contents(session, api_base, course_id, folder_id, headers):
    """Recursively fetch contents of a folder."""
    try:
        outputs = []
        async with session.get(
            f"{api_base}/get/folder_contentsv2?course_id={course_id}&parent_id={folder_id}",
            headers=headers
        ) as response:
            j = await response.json()
            tasks = []
            
            if "data" in j:
                for item in j["data"]:
                    # Process individual items
                    tasks.append(fetch_item_details(session, api_base, course_id, item, headers))
                    # Recursively process subfolders
                    if item.get("material_type") == "FOLDER":
                        tasks.append(fetch_folder_contents(session, api_base, course_id, item["id"], headers))

            if tasks:
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        outputs.extend(res)

        return outputs

    except Exception as e:
        logger.error(f"Error fetching folder contents: {e}")
        return []

async def v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start, end, pricing, input2, m1, m2):
    """Process and extract course content."""
    try:
        progress_msg = await message.reply_text(
            "🔄 <b>Processing Large Batch</b>\n"
            f"└─ Initializing batch: <code>{sanitized_course_name}</code>"
        )

        async with aiohttp.ClientSession() as session:
            # Fetch root folder contents
            async with session.get(
                f"{api_base}/get/folder_contentsv2?course_id={raw_text2}&parent_id=-1",
                headers=hdr1
            ) as res2:
                j2 = await res2.json()

            if not j2.get("data"):
                await progress_msg.edit_text(
                    "❌ <b>No Content Found</b>\n\n"
                    "Try switching to v3 and retry."
                )
                return

            # Process all content
            all_outputs = []
            tasks = []
            
            if "data" in j2:
                total_items = len(j2["data"])
                processed = 0
                
                for item in j2["data"]:
                    tasks.append(fetch_item_details(session, api_base, raw_text2, item, hdr1))
                    if item["material_type"] == "FOLDER":
                        tasks.append(fetch_folder_contents(session, api_base, raw_text2, item["id"], hdr1))
                    
                    processed += 1
                    if processed % 5 == 0:  # Update progress every 5 items
                        await progress_msg.edit_text(
                            "🔄 <b>Processing Large Batch</b>\n"
                            f"├─ Progress: {processed}/{total_items}\n"
                            f"└─ Current: <code>{item.get('Title', 'Unknown')}</code>"
                        )

            if tasks:
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        all_outputs.extend(res)

            if not all_outputs:
                await progress_msg.edit_text("❌ <b>No content found in this batch</b>")
                return

            # Count content types
            video_count = sum(1 for url in all_outputs if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.mpd']))
            pdf_count = sum(1 for url in all_outputs if '.pdf' in url.lower())
            encrypted_count = sum(1 for url in all_outputs if '*' in url)

            # Save content to file
            file_name = f"{app_name}_{sanitized_course_name}_{int(datetime.now().timestamp())}.txt"
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_outputs))

            # Calculate duration
            end_time = datetime.now()
            duration = end_time - datetime.fromtimestamp(start_time)
            minutes, seconds = divmod(duration.total_seconds(), 60)

            # Prepare caption
            caption = (
                f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
                f"📱 <b>APP:</b> {app_name}\n"
                f"📚 <b>BATCH:</b> {sanitized_course_name}\n"
                f"⏱ <b>EXTRACTION TIME:</b> {int(minutes):02d}:{int(seconds):02d}\n"
                f"📅 <b>DATE:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
                f"📊 <b>CONTENT STATS</b>\n"
                f"├─ 📁 Total Links: {len(all_outputs)}\n"
                f"├─ 🎬 Videos: {video_count}\n"
                f"├─ 📄 PDFs: {pdf_count}\n"
                f"└─ 🔐 Encrypted: {encrypted_count}\n\n"
                f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
                f"<code>╾───• {BOT_TEXT} •───╼</code>"
            )

            # Send file
            await message.reply_document(
                document=file_name,
                caption=caption
            )
            await app.send_document(PREMIUM_LOGS, file_name, caption=caption)

            # Cleanup
            try:
                os.remove(file_name)
            except:
                pass

            # Delete temporary messages
            for msg in [input2, m1, m2]:
                try:
                    await msg.delete()
                except:
                    pass

            await progress_msg.edit_text(
                "✅ <b>Extraction completed successfully!</b>\n\n"
                f"📊 𝗙𝗶𝗻𝗮𝗹 𝗦𝘁𝗮𝘁𝘂𝘀:\n"
                f"📚 Processed: {total_items} items\n"
                f"📤 File has been uploaded\n\n"
                f"Thank you for using @IFSAshuAbhiBot Extractor Pro! 🌟"
            )

    except Exception as e:
        logger.error(f"Error in v2_new: {e}")
        await message.reply_text(
            "❌ <b>An error occurred</b>\n\n"
            f"Error: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )
                              
