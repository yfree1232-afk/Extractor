import requests, os, sys, re
import json, asyncio
import subprocess
import datetime
import time
import logging
from typing import List, Dict, Tuple, Any
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from Extractor import app
from config import PREMIUM_LOGS
import config
from pyrogram import Client, filters, idle
from pyrogram.types import Message
# from pyrogram.errors import ListenerTimeout
from subprocess import getstatusoutput
from datetime import datetime
import pytz
# from Extractor.modules.enc import process_file_content  # Add encryption import


join = config.join
india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")

THREADPOOL = ThreadPoolExecutor(max_workers=5000)

async def download_thumbnail(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        # Create a temporary filename
        thumb_path = f"thumb_{int(time.time())}.jpg"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                # Save the thumbnail
                with open(thumb_path, "wb") as f:
                    f.write(await response.read())
                return thumb_path
            return None
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return None

def create_html_file(file_name, batch_name, contents):
    tbody = ''
    parts = contents.split('\n')
    for part in parts:
        split_part = [item.strip() for item in part.split(':', 1)]
    
        text = split_part[0] if split_part[0] else 'Untitled'
        url = split_part[1].strip() if len(split_part) > 1 and split_part[1].strip() else 'No URL'

        tbody += f'<tr><td>{text}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>'

    with open('Extractor/core/template.html', 'r') as fp:
        file_content = fp.read()
    title = batch_name.strip()
    with open(file_name, 'w') as fp:
        fp.write(file_content.replace('{{tbody_content}}', tbody).replace('{{batch_name}}', title))
        



#======================================================================================================================





async def fetch_cpwp_signed_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    MAX_RETRIES = 5  # Increased from 3 to 5
    TIMEOUT = 60  # Increased timeout to 60 seconds
    
    for attempt in range(MAX_RETRIES):
        params = {"url": url_val}
        try:
            async with session.get(
                "https://api.classplusapp.com/cams/uploader/video/jw-signed-url", 
                params=params, 
                headers=headers,
                timeout=TIMEOUT
            ) as response:
                if response.status == 429:  # Rate limit
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
                    await asyncio.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                response_json = await response.json()
                signed_url = response_json.get("url") or response_json.get('drmUrls', {}).get('manifestUrl')
                if signed_url:
                    return signed_url
                
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching signed URL for {name} (Attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = min(2 ** attempt, 30)
                await asyncio.sleep(wait_time)
        except Exception as e:
            logging.error(f"Error fetching signed URL for {name}: {e} (Attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = min(2 ** attempt, 30)
                await asyncio.sleep(wait_time)

    logging.error(f"Failed to fetch signed URL for {name} after {MAX_RETRIES} attempts.")
    return None

async def process_cpwp_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    """Process video URLs"""
    try:
        if url_val.endswith(('.m3u8', '.mp4', '.mpd')):
            return f"{name}:{url_val}\n"
            
        # For special cases like testbook or drm content
        if "testbook.com" in url_val or "classplusapp.com/drm" in url_val:
            return f"{name}:{url_val}\n"
            
        return f"{name}:{url_val}\n"
        
    except Exception as e:
        logging.error(f"Error processing URL for {name}: {e}")
        return None


async def get_cpwp_course_content(session: aiohttp.ClientSession, headers: Dict[str, str], Batch_Token: str, folder_id: int = 0, limit: int = 9999999999, retry_count: int = 0) -> Tuple[List[str], int, int, int]:
    MAX_RETRIES = 5
    TIMEOUT = 120
    fetched_urls: set[str] = set()
    results: List[str] = []
    video_count = 0
    pdf_count = 0
    image_count = 0
    content_tasks: List[Tuple[int, asyncio.Task[str | None]]] = []
    folder_tasks: List[Tuple[int, asyncio.Task[List[str]]]] = []
     
    try:
        content_api = f'https://api.classplusapp.com/v2/course/preview/content/list/{Batch_Token}'
        params = {'folderId': folder_id, 'limit': limit}

        async with session.get(content_api, params=params, headers=headers, timeout=TIMEOUT) as res:
            if res.status == 429:
                wait_time = min(2 ** retry_count, 30)
                await asyncio.sleep(wait_time)
                return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1)
                
            res.raise_for_status()
            res_json = await res.json()
            contents: List[Dict[str, Any]] = res_json['data']

            chunk_size = 5
            for i in range(0, len(contents), chunk_size):
                chunk = contents[i:i + chunk_size]
                
                for content in chunk:
                    if content['contentType'] == 1:  # Folder
                        folder_task = asyncio.create_task(get_cpwp_course_content(session, headers, Batch_Token, content['id'], retry_count=0))
                        folder_tasks.append((content['id'], folder_task))
                    else:
                        name: str = content['name']
                        url_val: str | None = content.get('url') or content.get('thumbnailUrl')

                        if not url_val:
                            logging.warning(f"No URL found for content: {name}")
                            continue
                            
                        if "media-cdn.classplusapp.com/tencent/" in url_val:
                            url_val = url_val.rsplit('/', 1)[0] + "/master.m3u8"
                        elif "media-cdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                            identifier = url_val.split('/')[-3]
                            url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/{identifier}/master.m3u8'
                        elif "tencdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                            identifier = url_val.split('/')[-2]
                            url_val = f'https://media-cdn.classplusapp.com/tencent/{identifier}/master.m3u8'
                        elif "4b06bf8d61c41f8310af9b2624459378203740932b456b07fcf817b737fbae27" in url_val and url_val.endswith('.jpeg'):
                            video_id = url_val.split('/')[-1].split('.')[0]
                            url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/b08bad9ff8d969639b2e43d5769342cc62b510c4345d2f7f153bec53be84fe35/{video_id}/master.m3u8'
                        elif "cpvideocdn.testbook.com" in url_val and url_val.endswith('.png'):
                            match = re.search(r'/streams/([a-f0-9]{24})/', url_val)
                            video_id = match.group(1) if match else url_val.split('/')[-2]
                            url_val = f'https://cpvod.testbook.com/{video_id}/playlist.m3u8'
                        elif "media-cdn.classplusapp.com/drm/" in url_val and url_val.endswith('.png'):
                            video_id = url_val.split('/')[-3]
                            url_val = f'https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8'
                        elif "https://media-cdn.classplusapp.com" in url_val and ("cc/" in url_val or "lc/" in url_val or "uc/" in url_val or "dy/" in url_val) and url_val.endswith('.png'):
                            url_val = url_val.replace('thumbnail.png', 'master.m3u8')
                        elif "https://tb-video.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                            video_id = url_val.split('/')[-1].split('.')[0]
                            url_val = f'https://tb-video.classplusapp.com/{video_id}/master.m3u8'

                        if url_val.endswith(("master.m3u8", "playlist.m3u8")) and url_val not in fetched_urls:
                            fetched_urls.add(url_val)
                            headers2 = { 'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'}
                            task = asyncio.create_task(process_cpwp_url(url_val, name, session, headers2))
                            content_tasks.append((content['id'], task))
                            video_count += 1
                        else:
                            if url_val:
                                fetched_urls.add(url_val)
                                results.append(f"{name}:{url_val}\n")
                                if url_val.endswith('.pdf'):
                                    pdf_count += 1
                                else:
                                    image_count += 1
                
                await asyncio.sleep(1)  # Rate limiting delay
                            
    except asyncio.TimeoutError:
        logging.error(f"Timeout while fetching content list for folder {folder_id}")
        if retry_count < MAX_RETRIES:
            wait_time = min(2 ** retry_count, 30)
            await asyncio.sleep(wait_time)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1)
        return [], 0, 0, 0
                                
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        if retry_count < MAX_RETRIES:
            logging.info(f"Retrying folder {folder_id} (Attempt {retry_count + 1}/{MAX_RETRIES})")
            wait_time = min(2 ** retry_count, 30)
            await asyncio.sleep(wait_time)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1)
        else:
            logging.error(f"Failed to retrieve folder {folder_id} after {MAX_RETRIES} retries.")
            return [], 0, 0, 0
            
    # Process tasks in chunks
    chunk_size = 10
    for i in range(0, len(content_tasks), chunk_size):
        chunk = content_tasks[i:i + chunk_size]
        try:
            chunk_results = await asyncio.wait_for(
                asyncio.gather(*(task for _, task in chunk), return_exceptions=True),
                timeout=TIMEOUT
            )
            
            for result in chunk_results:
                if isinstance(result, Exception):
                    logging.error(f"Task failed with exception: {result}")
                elif result:
                    results.append(result)
            
            await asyncio.sleep(1)
            
        except asyncio.TimeoutError:
            logging.error(f"Timeout while gathering results chunk {i//chunk_size + 1}")
            continue
    
    # Process folder tasks
    for i in range(0, len(folder_tasks), chunk_size):
        chunk = folder_tasks[i:i + chunk_size]
        try:
            chunk_results = await asyncio.wait_for(
                asyncio.gather(*(task for _, task in chunk), return_exceptions=True),
                timeout=TIMEOUT
            )
            
            for folder_id, result in zip([fid for fid, _ in chunk], chunk_results):
                if isinstance(result, Exception):
                    logging.error(f"Folder task failed with exception: {result}")
                else:
                    nested_results, nested_video_count, nested_pdf_count, nested_image_count = result
                    if nested_results:
                        results.extend(nested_results)
                    video_count += nested_video_count
                    pdf_count += nested_pdf_count
                    image_count += nested_image_count
            
            await asyncio.sleep(1)
            
        except asyncio.TimeoutError:
            logging.error(f"Timeout while gathering folder results chunk {i//chunk_size + 1}")
            continue

    return results, video_count, pdf_count, image_count
    

    
async def process_cpwp(bot: Client, m: Message, user_id: int):
    # Add channel ID at the top
    CHANNEL_ID = -1002601604234
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip',
        'accept-language': 'EN',
        'api-version': '35',
        'app-version': '1.4.73.2',
        'build-number': '35',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'device-details': 'Xiaomi_Redmi 7_SDK-32',
        'device-id': 'c28d3cb16bbdac01',
        'host': 'api.classplusapp.com',
        'region': 'IN',
        'user-agent': 'Mobile-Android',
        'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c',
        'x-access-token': 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTIyMDc4ODg0LCJvcmdJZCI6NzExNTI4LCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTg2MDAzOTAyODgiLCJuYW1lIjoiU2Fua2V0IFNvbmFyIiwiZW1haWwiOiJoanMuc2Fua2V0QGdtYWlsLmNvbSIsImlzSW50ZXJuYXRpb25hbCI6MCwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiY291bnRyeUlTTyI6IjkxIiwidGltZXpvbmUiOiJHTVQrNTozMCIsImlzRGl5Ijp0cnVlLCJvcmdDb2RlIjoidWphbGFmIiwiaXNEaXlTdWJhZG1pbiI6MCwiZmluZ2VycHJpbnRJZCI6IjE3MjAxMDU1NjkwMjYiLCJpYXQiOjE3NDkyNTUzOTUsImV4cCI6MTc0OTg2MDE5NX0.uKdyXfFDtcdyaUItjc_G1ALYwtKxVyuG_SnPhRPa2cNy9Tzd0TaXdXNw1d2cUurv'
    }

    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=1000, loop=loop)
    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = None
        try:
            # Get user info at the start
            user = await bot.get_users(user_id)
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
            
            editable = await m.reply_text("**Enter ORG Code Of Your Classplus App**")
            
            try:
                input1 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                org_code = input1.text.lower()
                await input1.delete(True)
            except ListenerTimeout:
                await editable.edit("**Timeout! You took too long to respond**")
                return
            except Exception as e:
                logging.exception("Error during input1 listening:")
                try:
                    await editable.edit(f"**Error: {e}**")
                except:
                    logging.error(f"Failed to send error message to user: {e}")
                return

            hash_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://qsvfn.courses.store/?mainCategory=0&subCatList=[130504,62442]',
                'Sec-CH-UA': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            }
            
            async with session.get(f"https://{org_code}.courses.store", headers=hash_headers) as response:
                html_text = await response.text()
                hash_match = re.search(r'"hash":"(.*?)"', html_text)

                if hash_match:
                    token = hash_match.group(1)
                    all_courses = []
                    page = 0
                    page_size = 100  # Increased page size
                    
                    try:
                        # First try the new API endpoint
                        async with session.get(
                            f"https://api.classplusapp.com/v2/course/search/published?limit={page_size}&offset={page}&sortBy=courseCreationDate&status=published", 
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                res_json = await response.json()
                                courses = res_json.get('data', {}).get('courses', [])
                                if courses:
                                    all_courses.extend(courses)
                            else:
                                # If new API fails, try the old endpoint
                                while True:
                                    async with session.get(
                                        f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit={page_size}&page={page}", 
                                        headers=headers
                                    ) as response:
                                        if response.status == 200:
                                            res_json = await response.json()
                                            courses = res_json.get('data', {}).get('coursesData', [])
                                            
                                            if not courses:  # No more courses to fetch
                                                break
                                                
                                            all_courses.extend(courses)
                                            page += 1
                                            
                                            if len(courses) < page_size:  # Last page
                                                break
                                        else:
                                            break

                        if not all_courses:
                            raise Exception("No batches found! Please check if the org code is correct.")

                        # Sort courses by name
                        all_courses.sort(key=lambda x: x.get('name', '').lower())

                        # Split courses into chunks of 20 for display
                        chunks = [all_courses[i:i + 20] for i in range(0, len(all_courses), 20)]
                        all_indices = []
                        
                        initial_msg = await m.reply_text(f"**📚 Found {len(all_courses)} batches\nSending batch list in {len(chunks)} parts...**")
                        await asyncio.sleep(2)  # Small delay before starting
                        await initial_msg.delete()
                        
                        last_status_msg = None
                        for chunk_num, chunk in enumerate(chunks, 1):
                            text = f'📚 **Available Batches (Page {chunk_num}/{len(chunks)})**\n\n'
                            
                            for cnt, course in enumerate(chunk, 1 + (chunk_num-1)*20):
                                name = course.get('name', 'Untitled')
                                price = course.get('finalPrice', 'N/A')
                                text += f"{cnt}. ```\n{name} 💵₹{price}```\n"
                                all_indices.append(str(cnt))
                            
                            if chunk_num == len(chunks):  # Last chunk
                                copy_paste_format = "&".join(all_indices)
                                text += f"\n**For Multiple Batches Copy This** 👇\n`{copy_paste_format}`"
                            
                            # Send each chunk as a separate message
                            try:
                                if chunk_num == 1:  # First chunk
                                    await editable.edit(f"**Send index number of the Category Name\n\n{text}\n\nIf Your Batch Not Listed Then Enter Your Batch Name\n\nFor multiple batches, enter indices separated by & (e.g. 1&2&3)**")
                                else:
                                    await m.reply_text(text)
                                
                                # Add 5-second delay between chunks, except for the last one
                                if chunk_num < len(chunks):
                                    # Delete previous status message if it exists
                                    if last_status_msg:
                                        try:
                                            await last_status_msg.delete()
                                        except:
                                            pass
                                    last_status_msg = await m.reply_text(f"**📤 Sent {chunk_num}/{len(chunks)} parts...\nPlease wait 5 seconds...**")
                                    await asyncio.sleep(5)
                            except Exception as e:
                                print(f"Error in chunk {chunk_num}: {str(e)}")
                                continue
                        
                        # Delete the final status message
                        if last_status_msg:
                            try:
                                await last_status_msg.delete()
                            except:
                                pass

                        # Get batch selection from user
                        try:
                            batch_input = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=300)
                            raw_text2 = batch_input.text
                            await batch_input.delete(True)
                        except ListenerTimeout:
                            await editable.edit("**Timeout! You took too long to respond**")
                            return
                        except Exception as e:
                            logging.exception("Error during batch selection:")
                            await editable.edit(f"**Error: {e}**")
                            return

                    except Exception as e:
                        error_msg = f"**Error : {e}**"
                        if editable:
                            try:
                                await editable.edit(error_msg)
                            except:
                                await m.reply_text(error_msg)
                        else:
                            await m.reply_text(error_msg)
                        return

                else:
                    raise Exception("Didn't Find Any Course")

            # Handle multiple batch indices
            batch_indices = raw_text2.split('&')
            total_batches = len(batch_indices)
            processed_batches = 0
            last_wait_msg = None
            
            # Show initial status
            initial_extract_msg = await m.reply_text(f"**📥 Starting extraction of {total_batches} batches\nPlease wait, this may take some time...**")
            await asyncio.sleep(2)
            await initial_extract_msg.delete()
            
            # Process each batch separately
            for batch_index in batch_indices:
                batch_index = batch_index.strip()
                start_time = time.time()
                thumb_path = None
                
                # Add delay between batches except for the first one
                if processed_batches > 0:
                    # Delete previous wait message if it exists
                    if last_wait_msg:
                        try:
                            await last_wait_msg.delete()
                        except:
                            pass
                    last_wait_msg = await m.reply_text(f"**⏳ Waiting 5 seconds before next batch...\n📊 Progress: {processed_batches}/{total_batches} batches done**")
                    await asyncio.sleep(5)
                    await last_wait_msg.delete()
                
                # Download thumbnail for this batch
                if config.THUMB_URL:
                    thumb_path = await download_thumbnail(session, config.THUMB_URL)
                
                if batch_index.isdigit() and int(batch_index) <= len(all_courses):
                    selected_course_index = int(batch_index)
                    course = all_courses[selected_course_index - 1]
                    selected_batch_id = course['id']
                    selected_batch_name = course['name']
                    clean_batch_name = selected_batch_name.replace("/", "-").replace("|", "-")
                    
                    status_msg = await m.reply_text(
                        f"**📥 Extracting Batch {processed_batches + 1}/{total_batches}**\n"
                        f"**Name:** `{selected_batch_name}`"
                    )

                    batch_headers = {
                        'Accept': 'application/json, text/plain, */*',
                        'region': 'IN',
                        'accept-language': 'EN',
                        'Api-Version': '22',
                        'tutorWebsiteDomain': f'https://{org_code}.courses.store'
                    }
                        
                    params = {
                        'courseId': f'{selected_batch_id}',
                    }

                    try:
                        async with session.get(f"https://api.classplusapp.com/v2/course/preview/org/info", params=params, headers=batch_headers) as response:
                            if response.status == 200:
                                res_json = await response.json()
                                Batch_Token = res_json['data']['hash']
                                App_Name = res_json['data']['name']

                                course_content, video_count, pdf_count, image_count = await get_cpwp_course_content(session, headers, Batch_Token)
                                
                                if course_content:
                                    # Create individual file for this batch
                                    batch_filename = f"{clean_batch_name}_{batch_index}.txt"
                                    original_filename = f"{clean_batch_name}_{batch_index}_original.txt"
                                    
                                    # Save original content for logs
                                    with open(original_filename, 'w', encoding='utf-8') as f:
                                        f.write(''.join(course_content))

                                    # Create unencrypted content for user
                                    content = ''.join(course_content)
                                    # encrypted_content = await process_file_content(content, encrypt=True)  # Encryption skipped as per user request
                                    
                                    # Save unencrypted content for user
                                    with open(batch_filename, 'w', encoding='utf-8') as f:
                                        f.write(content)

                                    end_time = time.time()
                                    response_time = end_time - start_time
                                    minutes = int(response_time // 60)
                                    seconds = int(response_time % 60)

                                    if minutes == 0:
                                        if seconds < 1:
                                            formatted_time = f"{response_time:.2f} seconds"
                                        else:
                                            formatted_time = f"{seconds} seconds"
                                    else:
                                        formatted_time = f"{minutes} minutes {seconds} seconds"

                                    caption = (f"࿇ ══━━{mention}━━══ ࿇\n\n"
                                             f"🌀 **Aᴘᴘ Nᴀᴍᴇ** : {App_Name}\n"
                                             f"🔑 **Oʀɢ Cᴏᴅᴇ** : `{org_code}`\n"
                                             f"============================\n\n"
                                             f"🎯 **Bᴀᴛᴄʜ Nᴀᴍᴇ** : `{clean_batch_name}`\n"
                                             f"<blockquote>🎬 : {video_count} | 📁 : {pdf_count} | 🖼 : {image_count}</blockquote>\n\n"
                                           f"🌐 **Jᴏɪɴ Us** : {join}\n"
                                             f"⌛ **Tɪᴍᴇ Tᴀᴋᴇɴ** : {formatted_time}</blockquote>\n\n"
                                             f"❄️ **Dᴀᴛᴇ** : {time_new}")
                                            
                                    try:
                                        # Send unencrypted file to user
                                        with open(batch_filename, 'rb') as f:
                                            await m.reply_document(
                                                document=f, 
                                                caption=caption,
                                                thumb=thumb_path,
                                                file_name=f"{clean_batch_name}_{batch_index}.txt"
                                            )
                                            
                                        # Add summary message that stays for 5 seconds
                                        summary_msg = await m.reply_text(
                                            f"**📊 Content Summary for {clean_batch_name}**\n\n"
                                            f"🎬 **Total Videos/Images**: {video_count}\n"
                                            f"📁 **Total PDFs**: {pdf_count}\n\n"
                                            f"⌛ This message will disappear in 5 seconds..."
                                        )
                                        await asyncio.sleep(5)
                                        await summary_msg.delete()
                                        
                                        # Send original file to logs
                                        with open(original_filename, 'rb') as f:
                                            await app.send_document(
                                                chat_id=PREMIUM_LOGS,
                                                document=f,
                                                caption=f"🔓 **Original Decrypted Version**\n\n{caption}",
                                                thumb=thumb_path,
                                                file_name=f"{clean_batch_name}_{batch_index}_original.txt"
                                            )
                                    except Exception as e:
                                        print(f"Error sending document: {e}")
                                        await m.reply_text(f"**Error sending file for batch {selected_batch_name}: {str(e)}**")
                                    finally:
                                        try:
                                            os.remove(batch_filename)
                                            os.remove(original_filename)
                                            if thumb_path and os.path.exists(thumb_path):
                                                os.remove(thumb_path)
                                        except:
                                            pass
                                else:
                                    await m.reply_text(f"**No content found in batch: {selected_batch_name}**")
                            else:
                                await m.reply_text(f"**Error fetching batch {selected_batch_name}: {response.text}**")
                    except Exception as e:
                            await m.reply_text(f"**Error processing batch {selected_batch_name}: {str(e)}**")
                    finally:
                            processed_batches += 1
                            try:
                                await status_msg.delete()
                            except:
                                pass
                else:
                    await m.reply_text(f"**Invalid batch index: {batch_index}**")

            await m.reply_text(f"**✅ Completed processing {processed_batches}/{total_batches} batches**")
            
            if editable:
                try:
                    await editable.delete()
                except:
                    pass
        except Exception as e:
            error_msg = f"**Error : {e}**"
            if editable:
                try:
                    await editable.edit(error_msg)
                except:
                    await m.reply_text(error_msg)
            else:
                await m.reply_text(error_msg)
            
        finally:
            await session.close()
            await CONNECTOR.close()
