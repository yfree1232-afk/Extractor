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

# Unified Mobile Emulation Cloudscraper
global_scraper = cloudscraper.create_scraper()
ANDROID_UA = "Dalvik/2.1.0 (Linux; U; Android 11; SM-G991B Build/RP1A.200720.012)"

def decrypt(enc):
    try:
        enc = b64decode(enc.split(':')[0])
        key = '638udh3829162018'.encode('utf-8')
        iv = 'fedcba9876543210'.encode('utf-8')
        if len(enc) == 0:
            return ""
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(enc), AES.block_size)
        return plaintext.decode('utf-8')
    except:
        return ""

def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        return f"Error decoding string: {e}"

def sync_fetch(url, headers):
    try:
        r = global_scraper.get(url, headers=headers)
        if r.status_code == 200:
            try:
                return r.json()
            except:
                soup = BeautifulSoup(r.text, 'html.parser')
                return json.loads(str(soup))
    except Exception as e:
        print(f"Sync fetch error: {e}")
    return {}

async def fetch(url, headers):
    return await asyncio.to_thread(sync_fetch, url, headers)

def sync_post(url, data, headers):
    try:
        return global_scraper.post(url, data=data, headers=headers).json()
    except Exception as e:
        return {}

def sync_get(url, headers):
    try:
        return global_scraper.get(url, headers=headers).json()
    except Exception as e:
        return {}

async def handle_course(api_base, bi, si, sn, topic, hdr1):
    ti = topic.get("topicid")
    tn = topic.get("topic_name")
    
    url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={bi}&subjectid={si}&topicid={ti}&conceptid=&start=-1"
    r3 = await fetch(url, hdr1)
    video_data = sorted(r3.get("data", []), key=lambda x: x.get("id", 0))  
    
    tasks = [process_video(api_base, bi, si, sn, ti, tn, video, hdr1) for video in video_data]
    results = await asyncio.gather(*tasks)
    
    return [line for lines in results if lines for line in lines]

async def process_video(api_base, bi, si, sn, ti, tn, video, hdr1):
    vi = video.get("id")
    vn = video.get("Title")
    lines = []
    
    try:
        r4 = await fetch(f"{api_base}/get/fetchVideoDetailsById?course_id={bi}&video_id={vi}&ytflag=0&folder_wise_course=0", hdr1)
        
        if not r4 or not r4.get("data"):
            return None

        vt = r4.get("data", {}).get("Title", "")
        vl = r4.get("data", {}).get("download_link", "")
        fl = r4.get("data", {}).get("video_id", "")
        
        if fl:
            dfl = decrypt(fl)
            if dfl:
                if '.m3u8' in dfl or '.mp4' in dfl or '/' in dfl:
                    final_link = f"https://appxsignurl.vercel.app/appx/{dfl}?appxv=3"
                else:
                    final_link = f"https://youtu.be/{dfl}"
                lines.append(f"{vt}:{final_link}\n")

        if vl:
            dvl = decrypt(vl)
            if dvl and ".pdf" not in dvl: 
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
                    if da and k2:
                        lines.append(f"{vt}:{da}*{k2}\n")
                elif a:
                    da = decrypt(a)
                    if da:
                        lines.append(f"{vt}:{da}\n")
        
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt == "PDF" or mt == "VIDEO":
                p1 = r4["data"].get("pdf_link", "")
                pk1 = r4["data"].get("pdf_encryption_key", "")
                p2 = r4["data"].get("pdf_link2", "")
                pk2 = r4["data"].get("pdf2_encryption_key", "")
                
                if p1 and pk1:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1)
                    if dp1:
                        if depk1 == "abcdefg":
                            lines.append(f"{vt}:{dp1}\n")
                        else:
                            lines.append(f"{vt}:{dp1}*{depk1}\n")
                if p2 and pk2:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2)
                    if dp2:
                        if depk2 == "abcdefg":
                            lines.append(f"{vt}:{dp2}\n")
                        else:
                            lines.append(f"{vt}:{dp2}*{depk2}\n")
                        
        return lines
    
    except Exception as e:
        return None

@app.on_message(filters.command(["appx", "appx4", "apiv4"]))
async def appex_v4_txt(app, message):
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
        
async def appex_v5_txt(app, message, api, name):
    api_base = api.replace("http://", "https://") if api.startswith(("http://", "https://")) else f"https://{api}"
    app_name = api_base.replace("http://", " ").replace("https://", " ").replace("api.classx.co.in"," ").replace("api.akamai.net.in", " ").replace("apinew.teachx.in", " ").replace("api.cloudflare.net.in", " ").replace("api.appx.co.in", " ").replace("/", " ")
    
    login_prompt = (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **Appx Mobile Emulator**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Now send your login credentials:**\n"
        "1) `mobile*password` for password login\n"
        "2) `10 digit mobile` for OTP login\n"
        "3) `JWT token` for direct login\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    
    input1 = await app.ask(message.chat.id, login_prompt)
    await forward_to_log(input1, "Appex Extractor")
    raw_text = input1.text.strip()
    
    # Base Mobile Emulator Headers
    mobile_headers = {
        "User-Agent": ANDROID_UA,
        "source": "APP",
        "device": "android",
        "appx-version": "5.0.0",
        "device-model": "SM-G991B",
        "os-version": "11",
        "Client-Service": "Appx",
        "Auth-Key": "appxapi"
    }

    userid = "-2"
    token = ""
    
    if '*' in raw_text:
        email, password = raw_text.split("*")
        raw_url = f"{api_base}/post/userLogin"
        login_hdr = mobile_headers.copy()
        login_hdr["Content-Type"] = "application/x-www-form-urlencoded"
        data = {"email": email, "password": password}
        
        try:
            # Cloudscraper POST inside thread to bypass 403
            response = await asyncio.to_thread(sync_post, raw_url, data, login_hdr)
            status = response.get("status")
            if status == 200:
                userid = str(response["data"]["userid"])
                token = response["data"]["token"]
            elif status == 203:
                second_api_url = f"{api_base}/post/userLogin?extra_details=0"
                second_data = {"source": "APP", "phone": email, "email": email, "password": password, "extra_details": "1"}
                second_response = await asyncio.to_thread(sync_post, second_api_url, second_data, login_hdr)
                if second_response.get("status") == 200:
                    userid = str(second_response["data"]["userid"])
                    token = second_response["data"]["token"]
                else:
                    return await message.reply_text("❌ Login failed. Invalid credentials.")
            else:
                return await message.reply_text("❌ Login failed. Invalid credentials.")
        except Exception as e:
            return await message.reply_text(f"❌ Login Failed: {str(e)}")
            
    elif raw_text.isdigit() and len(raw_text) == 10:
        url_otp = f"{api_base}/get/sendotp?phone={raw_text}"
        try:
            otp_json = await asyncio.to_thread(sync_get, url_otp, mobile_headers)
            if otp_json.get("status") != 200:
                return await message.reply_text("❌ Failed to send OTP. Ensure the number is registered.")
            
            otp_input = await app.ask(message.chat.id, "📲 **OTP sent successfully!**\nPlease enter the OTP you received:")
            otp_code = otp_input.text.strip()
            
            verify_url = f"{api_base}/get/otpverify?useremail={raw_text}&otp={otp_code}&device_id=WebBrowser17267591437616qmd1cxx313"
            verify_json = await asyncio.to_thread(sync_get, verify_url, mobile_headers)
            if verify_json.get("status") == 200:
                token = verify_json['user']['token']
                userid = str(verify_json['user'].get('userid', '-2'))
                await message.reply_text(f"✅ OTP Verified! Token extracted:\n`{token}`")
            else:
                return await message.reply_text("❌ Invalid OTP.")
        except Exception as e:
            return await message.reply_text(f"❌ OTP Process Failed: {str(e)}")
            
    else:
        userid = "extracted_userid_from_token"
        token = raw_text

    # Complete Mobile Request Headers
    hdr1 = mobile_headers.copy()
    hdr1["Authorization"] = token
    hdr1["User-ID"] = userid
        
    try:
        r = None
        for attempt in range(5):
            # Probe API for courses, wrapped in threadpool to prevent freezing
            def get_mycourse(url, h):
                return global_scraper.get(url, headers=h)
            
            r = await asyncio.to_thread(get_mycourse, f"{api_base}/get/mycoursev2?userid={userid}", hdr1)
            
            if r.status_code == 429:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            break
            
        if r.status_code != 200:
            return await message.reply_text(f"❌ **Server blocked the request!**\nStatus: {r.status_code}\nResponse:\n`{r.text[:500]}`")
        mc1 = r.json()

    except Exception as e:
        return await message.reply_text(f"❌ **Course Fetching Error**\n`{str(e)}`")

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
        await app.send_document(message.chat.id, document=file_path, caption="📚 Batch list exported to file due to large size")
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
        return

    batch_ids = input2.text.strip().split("&")
    batch_ids = [batch.strip() for batch in batch_ids if batch.strip() in valid_ids]

    if not batch_ids:
        return

    m1 = await message.reply_text("Processing your requested batches...")

    for raw_text2 in batch_ids:
        m2 = await message.reply_text(f"Extracting batch `{raw_text2}`...")
        start_time = time.time()
        
        course_info = next((ct for ct in mc1["data"] if ct.get("id") == raw_text2), {})
        course_name = course_info.get("course_name", "Course")
        thumbnail = course_info.get("course_thumbnail", "")
        start_date = course_info.get("start_date", "")
        end_date = course_info.get("end_date", "")
        price = course_info.get("price", "N/A")
        
        try:
            # Auto Detection Logic: Try course_by_id first, fallback if invalid
            def get_course_by_id(url, h):
                return global_scraper.get(url, headers=h)
                
            r = await asyncio.to_thread(get_course_by_id, f"{api_base}/get/course_by_id?id={raw_text2}", hdr1)
            try:
                r_json = r.json()
            except:
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
                
                with open(filename1, 'w', encoding='utf-8') as f:
                    try:
                        r1 = await fetch(f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={raw_text2}&start=-1", hdr1)
            
                        for subject in r1.get("data", []):
                            si = subject.get("subjectid")
                            sn = subject.get("subject_name")

                            r2 = await fetch(f"{api_base}/get/alltopicfrmlivecourseclass?courseid={raw_text2}&subjectid={si}&start=-1", hdr1)
                            topics = sorted(r2.get("data", []), key=lambda x: x.get("topicid", 0))

                            tasks = [handle_course(api_base, raw_text2, si, sn, t, hdr1) for t in topics]
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
                    pass
                finally:
                    if os.path.exists(filename1):
                        os.remove(filename1)
                        
        except Exception as e:
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
