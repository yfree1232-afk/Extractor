import requests
import threading 
import json
import cloudscraper
from pyrogram import filters
from Extractor import app
import os
import asyncio
import aiohttp
import base64
from Crypto.Cipher import AES
from Extractor.modules.mix import v2_new
from Extractor.core.utils import forward_to_log
from pyrogram.types import User
from Crypto.Util.Padding import unpad
from base64 import b64decode
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time 
from config import PREMIUM_LOGS, join
from datetime import datetime
import pytz




india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")


def decrypt(enc):
    enc = b64decode(enc.split(':')[0])
    key = '638udh3829162018'.encode('utf-8')
    iv = 'fedcba9876543210'.encode('utf-8')
    if len(enc) == 0:
        return ""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(enc), AES.block_size)
    return plaintext.decode('utf-8')

def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        return f"Error decoding string: {e}"
async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error fetching {url}: {response.status}")
                return {}
            content = await response.text()
            
            soup = BeautifulSoup(content, 'html.parser')
            return json.loads(str(soup))
    except Exception as e:
        print(f"An error occurred while fetching {url}: {str(e)}")
        return {}


async def handle_course(session, api_base, bi, si, sn, topic, hdr1):
    ti = topic.get("topicid")
    tn = topic.get("topic_name")
    
    url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={bi}&subjectid={si}&topicid={ti}&conceptid=&start=-1"
    r3 = await fetch(session, url, hdr1)
    video_data = sorted(r3.get("data", []), key=lambda x: x.get("id"))  

    
    tasks = [process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1) for video in video_data]
    results = await asyncio.gather(*tasks)
    
    return [line for lines in results if lines for line in lines]

async def process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1):
    vi = video.get("id")
    vn = video.get("Title")
    lines = []
    
    try:
        r4 = await fetch(session, f"{api_base}/get/fetchVideoDetailsById?course_id={bi}&video_id={vi}&ytflag=0&folder_wise_course=0", hdr1)
        
        if not r4 or not r4.get("data"):
            print(f"Skipping video ID {vi}: No data found.")
            return None

        vt = r4.get("data", {}).get("Title", "")
        vl = r4.get("data", {}).get("download_link", "")
        fl = r4.get("data", {}).get("video_id", "")
        
        if fl:
            dfl = decrypt(fl)
            final_link = f"https://youtu.be/{dfl}"
            lines.append(f"{vt}:{final_link}\n")

        if vl:
            dvl = decrypt(vl)
            if ".pdf" not in dvl: 
                lines.append(f"{vt}:{dvl}\n")
                 
        else:
            encrypted_links = r4.get("data", {}).get("encrypted_links", [])
            if encrypted_links:
                first_link = encrypted_links[0]
                a = first_link.get("path")
                k = first_link.get("key")
                if a and k:
                    da = decrypt(a)
                    k1 = decrypt(k)
                    k2 = decode_base64(k1)
                    lines.append(f"{vt}:{da}*{k2}\n")
                elif a:
                    da = decrypt(a)
                    lines.append(f"{vt}:{da}\n")
        
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt == "PDF":
                p1 = r4["data"].get("pdf_link", "")
                pk1 = r4["data"].get("pdf_encryption_key", "")
                p2 = r4["data"].get("pdf_link2", "")
                pk2 = r4["data"].get("pdf2_encryption_key", "")
                
                if p1 and pk1:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1)
                    if depk1 == "abcdefg":
                        lines.append(f"{vt}:{dp1}\n")
                    else:
                        lines.append(f"{vt}:{dp1}*{depk1}\n")
                if p2 and pk2:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2)
                    if depk2 == "abcdefg":
                        lines.append(f"{vt}:{dp2}\n")
                    else:
                        lines.append(f"{vt}:{dp2}*{depk2}\n")

        
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt == "VIDEO":
                p1 = r4["data"].get("pdf_link", "")
                pk1 = r4["data"].get("pdf_encryption_key", "")
                p2 = r4["data"].get("pdf_link2", "")
                pk2 = r4["data"].get("pdf2_encryption_key", "")
                
                if p1 and pk1:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1)
                    if depk1 == "abcdefg":
                        lines.append(f"{vt}:{dp1}\n")
                    else:
                        lines.append(f"{vt}:{dp1}*{depk1}\n")
                if p2 and pk2:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2)
                    if depk2 == "abcdefg":
                        lines.append(f"{vt}:{dp2}\n")
                    else:
                        lines.append(f"{vt}:{dp2}*{depk2}\n")
                        
        return lines
    
    except Exception as e:
        print(f"An error occurred while processing video ID {vi}: {str(e)}")
        return None

            
            
THREADPOOL = ThreadPoolExecutor(max_workers=1000)
@app.on_message(filters.command(["appx", "appx4", "apiv4"]))

async def appex_v4_txt(app, message):
    THREADPOOL = ThreadPoolExecutor(max_workers=1000)
    api_prompt = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 <b>ᴇɴᴛᴇʀ ᴀᴘɪ ᴜʀʟ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>ɪɴsᴛʀᴜᴄᴛɪᴏɴs:</b>\n"
        "• ᴅᴏɴ'ᴛ ɪɴᴄʟᴜᴅᴇ ʜᴛᴛᴘs://\n"
        "• ᴏɴʟʏ sᴇɴᴅ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ\n\n"
        "📌 <b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
        "<code>tcsexamzoneapi.classx.co.in</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    api = await app.ask(message.chat.id, text=api_prompt)
    api_txt = api.text
    name = api_txt.split('.')[0].replace("api", "") if api else api_txt.split('.')[0]
    if "api" in api_txt:
        await appex_v5_txt(app, message, api_txt, name)
    else:
        error_msg = (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "❌ <b>ɪɴᴠᴀʟɪᴅ ᴀᴘɪ ᴜʀʟ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "• ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴜʀʟ\n"
            "• ᴜsᴇ /findapi ᴛᴏ ɢᴇᴛ ᴄᴏʀʀᴇᴄᴛ ᴀᴘɪ\n\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        await app.send_message(message.chat.id, error_msg)
        
async def appex_v5_txt(app, message, api, name, predefined_credentials=None):
   
    api_base = api.replace("http://", "https://") if api.startswith(("http://", "https://")) else f"https://{api}"
    app_name = api_base.replace("http://", " ").replace("https://", " ").replace("api.classx.co.in"," ").replace("api.akamai.net.in", " ").replace("apinew.teachx.in", " ").replace("api.cloudflare.net.in", " ").replace("api.appx.co.in", " ").replace("/", " ")
    
    login_prompt = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎭 <b>PRO_TXT_EXTRATOR_BOT</b> 🎭\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>ʜᴏᴡ ᴛᴏ ʟᴏɢɪɴ:</b>\n\n"
        "1️⃣ ᴜsᴇ ɪᴅ & ᴘᴀssᴡᴏʀᴅ:\n"
        "   <code>ID*Password</code>\n\n"
        "2️⃣ ᴏʀ ᴜsᴇ ᴛᴏᴋᴇɴ ᴅɪʀᴇᴄᴛʟʏ\n\n"
        "📌 <b>ᴇxᴀᴍᴘʟᴇs:</b>\n"
        "• ɪᴅ/ᴘᴀss ➠ <code>9769696969*password123</code>\n"
        "• ᴛᴏᴋᴇɴ ➠ <code>eyJhbGciOiJIUzI1...</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    
    if predefined_credentials:
        raw_text = predefined_credentials
    else:
        input1 = await app.ask(message.chat.id, login_prompt)
        await forward_to_log(input1, "Appex Extractor")
        raw_text = input1.text.strip()
    
    if '*' in raw_text:
        email, password = raw_text.split("*")
        raw_url = f"{api_base}/post/userLogin"
        headers = {
            "Auth-Key": "appxapi",
            "User-Id": "-2",
            "Authorization": "",
            "User_app_category": "",
            "Language": "en",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "okhttp/4.9.1"
        }
        data = {"email": email, "password": password}
        
        try:
            response = requests.post(raw_url, data=data, headers=headers).json()
            status = response.get("status")

            if status == 200:
                userid = response["data"]["userid"]
                token = response["data"]["token"]
            
            elif status == 203:
                second_api_url = f"{api_base}/post/userLogin?extra_details=0"
                second_headers = {
                    "auth-key": "appxapi",
                    "client-service": "Appx",
                    "source": "website",
                    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
                    "accept": "*/*",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8"
                }
                second_data = {
                    "source": "website",
                    "phone": email,
                    "email": email,
                    "password": password,
                    "extra_details": "1"
                }
                
                second_response = requests.post(second_api_url, headers=second_headers, data=second_data).json()
                if second_response.get("status") == 200:
                    userid = second_response["data"]["userid"]
                    token = second_response["data"]["token"]
                else:
                    return await message.reply_text("❌ <b>Login Failed</b>\n\nInvalid Login Credentials.")
            else:
                return await message.reply_text(f"❌ <b>Login Failed</b>\n\nStatus Code: {status}")
        except Exception as e:
            error_msg = (
                "❌ <b>Login Failed</b>\n\n"
                f"Error: {str(e)}\n\n"
                "Please check your credentials and try again."
            )
            return await message.reply_text(error_msg)
                               
        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": "1234"
        }
        
    else:
        userid = "extracted_userid_from_token"
        token = raw_text
        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": userid
        }  
        
    scraper = cloudscraper.create_scraper() 
    try:
        mc1 = scraper.get(f"{api_base}/get/mycoursev2?userid={userid}", headers=hdr1).json()
        
    except json.JSONDecodeError as e:
        error_msg = (
            "❌ <b>An error occurred during extraction</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )
        return await message.reply_text(error_msg)
    except Exception as e:
        error_msg = (
            "❌ <b>An error occurred during extraction</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )
        return await message.reply_text(error_msg)

    batch_list = "📚 <b>ᴀᴠᴀɪʟᴀʙʟᴇ ʙᴀᴛᴄʜᴇs</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    valid_ids = []

    if "data" in mc1 and mc1["data"]:
        for ct in mc1["data"]:
            ci = ct.get("id")
            cn = ct.get("course_name")
            price = ct.get("price", "N/A")
            batch_list += f"┣━➤ <code>{ci}</code>\n┃   <b>{cn}</b>\n┃   💰 ₹{price}\n┃\n"
            valid_ids.append(ci)
    else:
        error_msg = "❌ <b>ɴᴏ ʙᴀᴛᴄʜᴇs ғᴏᴜɴᴅ!</b>\n\nᴘʟᴇᴀsᴇ ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ɪғ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪs ɪs ᴀɴ ᴇʀʀᴏʀ."
        return await message.reply_text(error_msg)

    success_msg = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>{app_name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>sᴛᴀᴛᴜs:</b> ʟᴏɢɪɴ sᴜᴄᴄᴇssғᴜʟ ✅\n\n"
        f"📡 <b>ᴀᴘɪ:</b>\n<code>{api_base}</code>\n\n"
        f"🔐 <b>ᴄʀᴇᴅᴇɴᴛɪᴀʟs:</b>\n<pre>{raw_text}</pre>\n"
        f"🔰 <b>Tᴏᴋᴇɴ:</b>\n<pre>{token}</pre>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"{batch_list}"
    )

    if len(batch_list) <= 4096:
        await app.send_message(PREMIUM_LOGS, success_msg)
        editable1 = await message.reply_text(success_msg)
    else:
        file_path = f"{app_name}_batches.txt"
        with open(file_path, "w") as file:
            file.write(f"{success_msg}\n\nToken: {token}")

        await app.send_document(
            message.chat.id,
            document=file_path,
            caption="📚 Batch list exported to file due to large size"
        )
        await app.send_document(PREMIUM_LOGS, document=file_path)
        editable1 = None

    batch_prompt = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 <b>ᴅᴏᴡɴʟᴏᴀᴅ ʙᴀᴛᴄʜᴇs</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>sɪɴɢʟᴇ ʙᴀᴛᴄʜ:</b>\n"
        "   • sᴇɴᴅ ᴏɴᴇ ɪᴅ\n\n"
        "2️⃣ <b>ᴍᴜʟᴛɪᴘʟᴇ ʙᴀᴛᴄʜᴇs:</b>\n"
        "   • sᴇᴘᴀʀᴀᴛᴇ ɪᴅs ᴡɪᴛʜ '&'\n"
        "   • ᴇxᴀᴍᴘʟᴇ: <code>123&456&789</code>\n\n"
        "📋 <b>ᴄᴏᴘʏ ᴀʟʟ ʙᴀᴛᴄʜᴇs:</b>\n"
        f"<code>{('&').join(valid_ids)}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    
    input2 = await app.ask(message.chat.id, batch_prompt)

    if not input2:
        await message.reply_text("**Invalid input. Please send valid batch IDs.**")
        await input2.delete(True)
        if editable1:
            await editable1.delete(True)
        return

    batch_ids = input2.text.strip().split("&")
    batch_ids = [batch.strip() for batch in batch_ids if batch.strip() in valid_ids]

    if not batch_ids:
        await message.reply_text("**Invalid batch ID(s). Please send valid batch IDs from the list.**")
        await input2.delete(True)
        if editable1:
            await editable1.delete(True)
        return

    m1 = await message.reply_text("Processing your requested batches...")

    # Process each batch ID sequentially like v3
    for raw_text2 in batch_ids:
        m2 = await message.reply_text(f"Extracting batch `{raw_text2}`...")
        start_time = time.time()
        
        # Get course details including thumbnail
        course_info = next((ct for ct in mc1["data"] if ct.get("id") == raw_text2), {})
        course_name = course_info.get("course_name", "Course")
        thumbnail = course_info.get("course_thumbnail", "")
        start_date = course_info.get("start_date", "")
        end_date = course_info.get("end_date", "")
        price = course_info.get("price", "N/A")
        
        try:
            r = scraper.get(f"{api_base}/get/course_by_id?id={raw_text2}", headers=hdr1)
            try:
                r_json = r.json()
            except:
                # If JSON parsing fails, try v2_new method
                sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
                await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start_date, end_date, price, input2, m1, m2)
                continue

            if not r_json.get("data"):
                sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
                await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start_date, end_date, price, input2, m1, m2)
                continue

            for i in r_json.get("data", []):
                txtn = i.get("course_name")
                filename = f"{raw_text2}_{txtn.replace(':', '_').replace('/', '_')}.txt"

                if '/' in filename:
                    filename1 = filename.replace("/", "").replace(" ", "_")
                else:
                    filename1 = filename
                
                async with aiohttp.ClientSession() as session:
                    with open(filename1, 'w') as f:
                        try:
                            r1 = await fetch(session, f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={raw_text2}&start=-1", hdr1)
                
                            for subject in r1.get("data", []):
                                si = subject.get("subjectid")
                                sn = subject.get("subject_name")

                                r2 = await fetch(session, f"{api_base}/get/alltopicfrmlivecourseclass?courseid={raw_text2}&subjectid={si}&start=-1", hdr1)
                                topics = sorted(r2.get("data", []), key=lambda x: x.get("topicid"))

                                tasks = [handle_course(session, api_base, raw_text2, si, sn, t, hdr1) for t in topics]
                                all_data = await asyncio.gather(*tasks)
                    
                                for data in all_data:
                                    if data:
                                        f.writelines(data)
            
                        except Exception as e:
                            print(f"An error occurred while processing batch {raw_text2}: {str(e)}")
                            await message.reply_text(f"⚠️ Error processing batch {raw_text2}. Trying alternative method...")
                            sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
                            await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start_date, end_date, price, input2, m1, m2)
                            continue
                        
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    print(f"Elapsed time: {elapsed_time:.1f} seconds")
                    
                    # Using v3's caption format
                    caption = (
                        "࿇ ══━━ 🏦 ━━══ ࿇\n\n"
                        f"🌀 **Aᴘᴘ Nᴀᴍᴇ** : {app_name}\n"
                        f"============================\n\n"
                        f"🎯 **Bᴀᴛᴄʜ Nᴀᴍᴇ** : `{raw_text2}_{txtn}`\n"
                        f"🌟 **Cᴏᴜʀsᴇ Tʜᴜᴍʙɴᴀɪʟ** : <a href={thumbnail}>Thumbnail</a>\n\n"
                        f"📅 **Sᴛᴀʀᴛ Dᴀᴛᴇ** : {start_date}\n"
                        f"📅 **Eɴᴅ Dᴀᴛᴇ** : {end_date}\n"
                        f"💰 **Pʀɪᴄᴇ** : ₹{price}\n\n"
                        f"🌐 **Jᴏɪɴ Us** : {join}\n"
                        f"⏱ **Tɪᴍᴇ Tᴀᴋᴇɴ** : {elapsed_time:.1f}s\n"
                        f"📅 **Dᴀᴛᴇ** : {time_new}\n"
                        "━━━━━━━━━━━━━━━━━━━━━\n"
                        "🔰 ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ @PRO_TXT_EXTRATOR_BOT"
                    )
                
                    try:
                        await app.send_document(message.chat.id, filename1, caption=caption)
                        await app.send_document(PREMIUM_LOGS, filename1, caption=caption)
                        
                    except Exception as e:
                        print(f"An error occurred while sending the document: {str(e)}")
                        await message.reply_text(f"⚠️ Error sending document for batch {raw_text2}")
                    
                    finally:
                        if os.path.exists(filename1):
                            os.remove(filename1)
                            
        except Exception as e:
            print(f"Error processing batch {raw_text2}: {str(e)}")
            await message.reply_text(f"⚠️ Failed to process batch {raw_text2}")
            sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
            await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start_date, end_date, price, input2, m1, m2)
        finally:
            try:
                await m2.delete()
            except:
                pass

    try:
        await input2.delete()
        await m1.delete()
    except:
        pass
