import logging
import os
import httpx
import time
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from config import PREMIUM_LOGS, join, BOT_TEXT, THUMB_URL
from typing import List, Dict, Any
from Extractor.core.utils import forward_to_log

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
ROOT_DIR = os.getcwd()
THUMB_PATH = "thumb.jpg"
TIMEOUT = 30
MAX_CONCURRENT_REQUESTS = 10  # Maximum concurrent requests
CHUNK_SIZE = 5  # Number of items to process in parallel

def safe_get(obj, *keys, default=None):
    """Safely get nested dictionary values"""
    try:
        for key in keys:
            if obj is None:
                return default
            obj = obj.get(key)
        return obj if obj is not None else default
    except (AttributeError, KeyError):
        return default

async def download_thumbnail():
    """Download thumbnail image if not already downloaded"""
    if not os.path.exists(THUMB_PATH):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(THUMB_URL)
                if response.status_code == 200:
                    with open(THUMB_PATH, 'wb') as f:
                        f.write(response.content)
                    logger.info("Thumbnail downloaded successfully")
                    return THUMB_PATH
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            return None
    return THUMB_PATH

async def make_request(url: str, headers=None, method="GET", data=None, timeout=TIMEOUT):
    """Make HTTP request with error handling"""
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=timeout)
            else:
                response = await client.post(url, headers=headers, data=data, timeout=timeout)
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        return None
    except Exception as e:
        logger.error(f"Request error: {e}")
        return None

class VideoProcessor:
    def __init__(self, headers: Dict[str, str], semaphore: asyncio.Semaphore):
        self.headers = headers
        self.semaphore = semaphore
        self.client = httpx.AsyncClient(timeout=TIMEOUT)

    async def process_video(self, item: Dict[str, Any]) -> tuple:
        """Process a single video item"""
        try:
            name = safe_get(item, "lessonName", default="Untitled").replace(":", " ")
            url = safe_get(item, "lessonUrl")
            ext = safe_get(item, "lessonExt")
            vid = safe_get(item, "id")

            if not url or not ext:
                return None

            if ext == "brightcove":
                async with self.semaphore:
                    token_response = await self.client.get(
                        f"https://spec.apnikaksha.net/api/v2/livestreamToken?base=web&module=batch&type=brightcove&vid={vid}",
                        headers=self.headers
                    )
                    if token_response.status_code == 200:
                        video_token = safe_get(token_response.json(), "data", "token")
                        if video_token:
                            stream_url = f"https://edge.api.brightcove.com/playback/v2/accounts/6415636611001/videos/{url}/master.m3u8?bcov_auth={video_token}"
                            return (name, stream_url)
            elif ext == "youtube":
                video_url = f"https://www.youtube.com/embed/{url}"
                return (name, video_url)

        except Exception as e:
            logger.error(f"Error processing video {name}: {e}")
        return None

    async def close(self):
        await self.client.aclose()

async def process_items_concurrently(items: List[Dict[str, Any]], processor_func, chunk_size: int = CHUNK_SIZE) -> List[tuple]:
    """Process items concurrently in chunks"""
    results = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        tasks = [processor_func(item) for item in chunk]
        chunk_results = await asyncio.gather(*tasks)
        results.extend([r for r in chunk_results if r])
    return results

class AKExtractor:
    def __init__(self):
        self.user_data = {}
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def process_subject_content(self, headers: Dict[str, str], batch_id: str, subject_id: str, topic_id: str) -> List[tuple]:
        """Process content for a subject concurrently"""
        results = []
        content_types = ["class", "notes"]
        
        for content_type in content_types:
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    response = await client.get(
                        f"https://spec.apnikaksha.net/api/v2/batch-detail/{batch_id}?subjectId={subject_id}&topicId={topic_id}&type={content_type}",
                        headers=headers
                    )
                    if response.status_code != 200:
                        continue

                    data = response.json()
                    if content_type == "class":
                        items = safe_get(data, "data", "class_list", "classes", default=[])
                        if items:
                            video_processor = VideoProcessor(headers, self.semaphore)
                            video_results = await process_items_concurrently(items, video_processor.process_video)
                            results.extend(video_results)
                            await video_processor.close()
                    else:
                        items = safe_get(data, "data", "notesDetails", default=[])
                        for item in items:
                            name = safe_get(item, "docTitle", default="Untitled").replace(":", " ")
                            url = safe_get(item, "docUrl")
                            if url:
                                results.append((name, url))

            except Exception as e:
                logger.error(f"Error processing content type {content_type}: {e}")

        return results

    async def process_batch(self, headers: Dict[str, str], batch_id: str, status_msg: Message) -> List[tuple]:
        """Process an entire batch concurrently"""
        all_results = []
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                # Fetch subjects
                response = await client.get(
                    f"https://spec.apnikaksha.net/api/v2/batch-subject/{batch_id}",
                    headers=headers
                )
                if response.status_code != 200:
                    return []

                subjects = safe_get(response.json(), "data", "batch_subject", default=[])
                total_subjects = len(subjects)
                processed = 0

                for subject in subjects:
                    subject_id = safe_get(subject, "id")
                    subject_name = safe_get(subject, "subjectName", default="Untitled")

                    if not subject_id:
                        continue

                    # Update progress
                    processed += 1
                    await status_msg.edit_text(
                        f"🔄 <b>Processing Batch</b>\n\n"
                        f"📊 Progress: {processed}/{total_subjects} subjects\n"
                        f"📚 Current: <code>{subject_name}</code>",
                        parse_mode=ParseMode.HTML
                    )

                    # Fetch topics
                    response = await client.get(
                        f"https://spec.apnikaksha.net/api/v2/batch-topic/{subject_id}",
                        headers=headers
                    )
                    if response.status_code != 200:
                        continue

                    topics = safe_get(response.json(), "data", "batch_topic", default=[])
                    
                    # Process topics concurrently
                    topic_tasks = []
                    for topic in topics:
                        topic_id = safe_get(topic, "id")
                        if topic_id:
                            topic_tasks.append(self.process_subject_content(headers, batch_id, subject_id, topic_id))
                    
                    if topic_tasks:
                        topic_results = await asyncio.gather(*topic_tasks)
                        for result in topic_results:
                            all_results.extend(result)

        except Exception as e:
            logger.error(f"Error processing batch: {e}")

        return all_results
    
    async def start_command(self, client: Client, message: Message):
        """Handle the /ak command"""
        # Clear any existing conversation
        if message.from_user.id in self.user_data:
            self.user_data.pop(message.from_user.id)

        # Store batch info
        batch_info = {}
        
        status_msg = await message.reply_text(
            "🔹 <b>UG EXTRACTOR PRO</b> 🔹\n\n"
            "Send login details in this format:\n"
            "📧 <code>email*password</code>\n\n"
            "<i>Example:</i>\n"
            "- <code>user@gmail.com*password123</code>",
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Get login credentials using Pyrogram client
            try:
                e_message = await client.ask(
                    message.chat.id,
                    "⌛ Waiting for login details...",
                    timeout=120
                )
                await forward_to_log(e_message, "AK Extractor")
                user_input = e_message.text.strip()
            except asyncio.TimeoutError:
                await status_msg.edit_text(
                    "❌ <b>Timeout Error</b>\n\n"
                    "Please try again with the command /ak",
                    parse_mode=ParseMode.HTML
                )
                return

            if '*' not in user_input:
                await status_msg.edit_text(
                    "❌ <b>Invalid Format</b>\n\n"
                    "Please send details in format: <code>email*password</code>",
                    parse_mode=ParseMode.HTML
                )
                return

            email, password = user_input.split('*', 1)
            await status_msg.edit_text(
                "🔄 <b>Logging in to ApniKaksha...</b>",
                parse_mode=ParseMode.HTML
            )

            # Login request using httpx client
            login_url = "https://spec.apnikaksha.net/api/v2/login-other"
            headers = {
                "Accept": "application/json",
                "origintype": "web",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            login_data = {
                "email": email,
                "password": password,
                "type": "kkweb",
                "deviceType": "web",
                "deviceVersion": "Chrome 133",
                "deviceModel": "chrome",
            }

            async with httpx.AsyncClient(timeout=TIMEOUT) as http_client:
                login_response = await http_client.post(
                    login_url,
                    headers=headers,
                    data=login_data
                )

                if login_response.status_code != 200:
                    await status_msg.edit_text(
                        "❌ <b>Login Failed</b>\n\n"
                        "Server error or invalid response",
                        parse_mode=ParseMode.HTML
                    )
                    return

                response_data = login_response.json()
                if response_data.get("responseCode") != 200:
                    await status_msg.edit_text(
                        "❌ <b>Login Failed</b>\n\n"
                        "Invalid credentials or server error",
                        parse_mode=ParseMode.HTML
                    )
                    return

                auth_token = safe_get(response_data, "data", "token")
                if not auth_token:
                    await status_msg.edit_text(
                        "❌ <b>Login Failed</b>\n\n"
                        "Could not get authentication token",
                        parse_mode=ParseMode.HTML
                    )
                    return

                # Update headers with token
                headers.update({
                    "Host": "spec.apnikaksha.net",
                    "token": auth_token,
                    "usertype": "2"
                })

                # Fetch batches using httpx client
                batches_response = await http_client.get(
                    "https://spec.apnikaksha.net/api/v2/my-batch",
                    headers=headers
                )

                if batches_response.status_code != 200:
                    await status_msg.edit_text(
                        "❌ <b>Error Fetching Batches</b>\n\n"
                        "Server error or invalid response",
                        parse_mode=ParseMode.HTML
                    )
                    return

                batches = safe_get(batches_response.json(), "data", "batchData", default=[])
                if not batches:
                    await status_msg.edit_text(
                        "❌ <b>No Batches Found</b>\n\n"
                        "Your account has no purchased batches.",
                        parse_mode=ParseMode.HTML
                    )
                    return

                # Format batch list and store batch info
                batch_list = ""
                for batch in batches:
                    batch_id = str(batch['id'])
                    batch_name = batch['batchName'].replace(" ", "_").replace("/", "-")  # Clean batch name for filename
                    batch_info[batch_id] = batch_name
                    batch_list += f"🔸 <code>{batch_id}</code> - <b>{batch['batchName']}</b>\n"

                await status_msg.edit_text(
                    "✅ <b>ApniKaksha Login Successful</b>\n\n"
                    f"🆔 <b>Email:</b> <code>{email}</code>\n\n"
                    "📚 <b>Available Batches:</b>\n\n"
                    f"{batch_list}\n"
                    "💡 Send the batch ID to download content",
                    parse_mode=ParseMode.HTML
                )

                # Get batch ID using Pyrogram client
                try:
                    batch_message = await client.ask(
                        message.chat.id,
                        "⌛ Waiting for batch ID...",
                        timeout=120
                    )
                    batch_id = batch_message.text.strip()
                except asyncio.TimeoutError:
                    await status_msg.edit_text(
                        "❌ <b>Timeout Error</b>\n\n"
                        "Please try again with the command /ak",
                        parse_mode=ParseMode.HTML
                    )
                    return

                if batch_id not in batch_info:
                    await status_msg.edit_text(
                        "❌ <b>Invalid Batch ID</b>\n\n"
                        "Please try again with a valid batch ID from the list.",
                        parse_mode=ParseMode.HTML
                    )
                    return

            # Process batch with concurrent requests
            start_time = time.time()
            results = await self.process_batch(headers, batch_id, status_msg)
            
            if not results:
                await status_msg.edit_text(
                    "❌ <b>No Content Found</b>\n\n"
                    "This batch might be empty or inaccessible.",
                    parse_mode=ParseMode.HTML
                )
                return

            # Write results to file using batch name
            batch_name = batch_info[batch_id]
            file_name = f"AK_{batch_name}-@CoreUG.txt"
            with open(file_name, "w", encoding='utf-8') as f:
                for name, url in results:
                    f.write(f"{name}: {url}\n")

            # Calculate stats
            end_time = time.time()
            elapsed_time = end_time - start_time
            mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'

            # Format caption with batch name
            caption = (
                "🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
                f"📱 <b>APP:</b> ApniKaksha\n"
                f"📚 <b>BATCH:</b> {batch_info[batch_id]}\n"
                f"⏱ <b>TIME TAKEN:</b> {elapsed_time:.1f}s\n"
                f"📅 <b>DATE:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n\n"
                f"📊 <b>CONTENT STATS</b>\n"
                f"└─ 📁 Total Items: {len(results)}\n\n"
                f"🚀 <b>Extracted by:</b> {mention}\n\n"
                f"<code>╾───• {BOT_TEXT} •───╼</code>"
            )

            # Send file
            await client.send_document(
                message.chat.id,
                document=file_name,
                caption=caption,
                thumb=await download_thumbnail() if await download_thumbnail() else None,
                parse_mode=ParseMode.HTML
            )

            await client.send_document(
                PREMIUM_LOGS,
                document=file_name,
                caption=caption,
                thumb=await download_thumbnail() if await download_thumbnail() else None,
                parse_mode=ParseMode.HTML
            )

            await status_msg.edit_text(
                "✅ <b>Extraction Completed!</b>\n\n"
                f"📊 Total Items: {len(results)}",
                parse_mode=ParseMode.HTML
            )

            # Cleanup
            try:
                os.remove(file_name)
            except Exception as e:
                logger.error(f"Error removing file: {e}")

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            error_message = (
                "❌ <b>An Error Occurred</b>\n\n"
                f"Error details: <code>{str(e)}</code>\n\n"
                "Please try again or contact support."
            )
            if 'status_msg' in locals():
                await status_msg.edit_text(error_message, parse_mode=ParseMode.HTML)
            else:
                await message.reply_text(error_message, parse_mode=ParseMode.HTML)

    async def handle_message(self, client: Client, message: Message):
        """Handle incoming messages based on conversation state"""
        user_id = message.from_user.id
        
        if user_id not in self.user_data:
            return
        
        state = self.user_data[user_id]['state']
        
        if state == State.AUTH:
            await self.handle_auth(client, message)
        elif state == State.BATCH_ID:
            await self.handle_batch_id(client, message)
        elif state == State.CONTENT_TYPE:
            await self.handle_content_type(client, message)

# Create a global instance
ak_extractor = AKExtractor()

async def ak_start(client: Client, message: Message):
    """Wrapper function for backward compatibility"""
    await ak_extractor.start_command(client, message)

def setup(app: Client):
    """Setup the AK extractor module"""
    @app.on_message(filters.command("ak"))
    async def ak_command(client, message):
        await ak_extractor.start_command(client, message)

    @app.on_message(filters.private & ~filters.command)
    async def handle_messages(client, message):
        await ak_extractor.handle_message(client, message)