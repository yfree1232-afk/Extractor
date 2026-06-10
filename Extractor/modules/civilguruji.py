import os
import re
import asyncio
import aiohttp
from pyrogram import Client, filters
from Extractor import app
from config import BOT_TEXT

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_. ')
    return name if name else "Unknown_Batch"

async def civil_guru(app, message):
    input1 = await app.ask(message.chat.id, text="Send **ID & Password** in this manner, otherwise, the bot will not respond.\n\nSend like this: **ID*Password**")
    raw_text = input1.text
    try:
        ph, pas = raw_text.split("*")
    except ValueError:
        await message.reply_text("Invalid format! Send as ID*Password")
        return
        
    await input1.delete(True)
    msg = await message.reply_text("Logging in...")
    
    url1 = "https://civilguruji.com/api/user/signin"
    payload1 = {
        "phoneNumber": "",
        "countryCode": "+91",
        "email": ph,
        "from": "email"
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://civilguruji.com/login",
        "Origin": "https://civilguruji.com",
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url1, json=payload1, headers=headers) as r1:
            data1 = await r1.json()
            if '_id' not in data1:
                await msg.edit_text("Login failed. Check ID/Password.")
                return
            uid = data1['_id']

        url2 = "https://civilguruji.com/api/user/signin-with-password"
        payload2 = {
            "userId": uid,
            "password": pas
        }
        async with session.post(url2, json=payload2, headers=headers) as r2:
            data2 = await r2.json()
            if 'access_token' not in data2:
                await msg.edit_text("Wrong password!")
                return
            token = data2['access_token']

        await msg.edit_text("**Login Successful. Fetching Batches...**")

        headers1 = headers.copy()
        headers1["X-Access-Token"] = token
        
        url3 = "https://civilguruji.com/api/course/list-purchased-courses"
        payload3 = {"userId": uid}

        async with session.post(url3, json=payload3, headers=headers1) as r3:
            courses_data = await r3.json()
            
        if not courses_data:
            await msg.edit_text("No purchased batches found!")
            return
            
        text = ''
        batches_list = []
        for cnt, data in enumerate(courses_data):
            batch_id = data.get('_id')
            batch_name = data.get('name')
            batches_list.append((batch_id, batch_name))
            text += f"{cnt + 1}. {batch_name}\n"
            
        course_details_file = f"{message.from_user.id}_civilguruji_courses.txt"
        with open(course_details_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        caption = (
            f"🎓 <b>CIVIL GURUJI COURSES</b> 🎓\n\n"
            f"📚 <b>TOTAL COURSES:</b> {len(courses_data)}\n\n"
            f"<code>╾───• @PRO_TXT_EXTRATOR_BOT •───╼</code>\n\n"
            "Send the index number to download course"
        )
        
        await msg.delete()
        doc_msg = await message.reply_document(
            document=course_details_file,
            caption=caption,
            file_name="civilguruji_courses.txt"
        )
        
        try:
            os.remove(course_details_file)
        except:
            pass
            
        try:
            input2 = await app.listen(chat_id=message.chat.id, filters=filters.user(message.from_user.id), timeout=120)
            user_choice = input2.text.strip()
            await input2.delete(True)
        except:
            await doc_msg.edit("❌ <b>Timeout!</b>\n\nYou took too long to respond.")
            return
            
        if not user_choice.isdigit() or not (1 <= int(user_choice) <= len(batches_list)):
            await doc_msg.edit("❌ <b>Invalid Input!</b>\n\nPlease send a valid index number.")
            return
            
        selected_idx = int(user_choice) - 1
        selected_batch_id, selected_batch_name = batches_list[selected_idx]
        clean_batch_name = sanitize_filename(selected_batch_name)
        
        status_msg = await message.reply_text(
            "🔄 <b>Processing Course</b>\n"
            f"└─ Current: <code>{selected_batch_name}</code>"
        )

        headers2 = headers1.copy()
        url4 = f"https://civilguruji.com/api/course/package/package-details/{selected_batch_id}"
        
        async with session.get(url4, headers=headers2) as r4:
            if r4.status != 200:
                await status_msg.edit("Failed to get course details.")
                return
            package_data = await r4.json()
            courses = package_data.get('courses', [])
            
        all_outputs = []
        
        for course in courses:
            c_id = course['course']['_id']
            c_name = course['course']['name']
            
            url5 = f"https://civilguruji.com/api/course/course-details/{c_id}"
            async with session.get(url5, headers=headers2) as r5:
                if r5.status != 200:
                    continue
                c_data = await r5.json()
                contents = c_data.get('courseDetail', {}).get('courseContents', [])
                
                all_outputs.append(f"\n{c_name}\n\n")
                
                for content in contents:
                    sub_contents = content.get('courseSubContents', [])
                    for sc in sub_contents:
                        n = sc.get('name', 'Unknown')
                        if sc.get('videoUrl'):
                            vurl = sc['videoUrl']
                            urls = re.findall(r'src="([^"]+)"', vurl)
                            if urls:
                                vurl = urls[0]
                            all_outputs.append(f"{n}:{vurl}\n")
                            
                        if sc.get('modelUrl'):
                            l = sc['modelUrl']
                            urls = re.findall(r'https?://\S+', l)
                            if urls:
                                murl = urls[0]
                            all_outputs.append(f"{n} Model:{murl}\n")

                        if sc.get('attachments'):
                            for d in sc['attachments']:
                                label = d.get('label', 'PDF')
                                aurl = d.get('data', '')
                                all_outputs.append(f"{n} {label}:{aurl}\n")
                                
        if not all_outputs:
            await status_msg.edit("❌ No videos or PDFs found in this batch.")
            return
            
        clean_file_name = f"{message.from_user.id}_{clean_batch_name}"
        content = ''.join(all_outputs)
        
        with open(f"{clean_file_name}.txt", 'w', encoding='utf-8') as f:
            f.write(content)
            
        video_count = sum(1 for line in all_outputs if ":" in line and "PDF:" not in line and "Model:" not in line and "http" in line)
        pdf_count = sum(1 for line in all_outputs if "PDF:" in line or "Model:" in line)
        total_links = video_count + pdf_count
        
        caption = (
            f"🎓 <b>CIVIL GURUJI EXTRACTED</b> 🎓\n\n"
            f"📚 <b>BATCH:</b> {selected_batch_name}\n\n"
            f"📊 <b>CONTENT STATS</b>\n"
            f"├─ 📁 Total Links: {total_links}\n"
            f"├─ 🎬 Videos: {video_count}\n"
            f"└─ 📄 PDFs/Models: {pdf_count}\n\n"
            f"🚀 <b>Extracted by</b>: @{(await app.get_me()).username}\n\n"
            f"<code>╾───• {BOT_TEXT} •───╼</code>"
        )
        
        with open(f"{clean_file_name}.txt", 'rb') as f:
            await doc_msg.delete()
            await status_msg.delete()
            await message.reply_document(
                document=f,
                caption=caption,
                file_name=f"{clean_batch_name}.txt"
            )
            
        try:
            os.remove(f"{clean_file_name}.txt")
        except:
            pass
