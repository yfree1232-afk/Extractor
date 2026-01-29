import os
import re
import base64
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pyrogram import Client, filters
from Extractor import app
from config import PREMIUM_LOGS
import pytz
from datetime import datetime

# Timezone setup
india_timezone = pytz.timezone('Asia/Kolkata')

# Fixed encryption key and IV (base64 decoded)
ENCRYPTION_KEY = base64.b64decode(b'isGRH8HAxrcXnnxbg1rBAeaA+aCdrhGuW87hdWBsDbI=')
IV = base64.b64decode(b'hdpz3/3Gd+c1qjZ+JlV3kg==')
IV_SIZE = 16  # Keep this for compatibility

async def encrypt_url(url: str) -> str:
    """Encrypt a URL using AES encryption"""
    if not url or not isinstance(url, str):
        return url
        
    try:
        # Use the fixed IV instead of generating random
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, IV)
        
        # Pad and encrypt the URL
        padded_data = pad(url.encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        
        # Encode encrypted data to base64 (no need to combine with IV since it's fixed)
        encoded = base64.b64encode(encrypted_data).decode()
        
        return f"UGPro_{encoded}"
    except Exception as e:
        print(f"Error encrypting URL: {e}")
        return url

async def decrypt_url(encrypted_str: str) -> str:
    """Decrypt an encrypted URL"""
    if not encrypted_str or not isinstance(encrypted_str, str):
        return encrypted_str
        
    if not encrypted_str.startswith("UGPro_"):
        return encrypted_str
        
    try:
        # Remove prefix and decode base64
        encrypted_data = base64.b64decode(encrypted_str[6:])
        
        # Use fixed IV for decryption
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, IV)
        decrypted_padded = cipher.decrypt(encrypted_data)
        decrypted = unpad(decrypted_padded, AES.block_size)
        
        return decrypted.decode()
    except Exception as e:
        print(f"Error decrypting URL: {e}")
        return encrypted_str

async def process_file_content(content: str, encrypt: bool = True) -> str:
    """Process file content and encrypt/decrypt URLs"""
    if not content:
        return content
        
    try:
        # Pattern to match URLs (both original and encrypted)
        url_pattern = r'(?:https://[^\s\n:]+|UGPro_[a-zA-Z0-9+/=]+)'
        
        # Find all URLs in the content
        urls = list(set(re.findall(url_pattern, content)))  # Remove duplicates
        new_content = content
        
        for url in urls:
            try:
                if encrypt:
                    processed_url = await encrypt_url(url) if not url.startswith("UGPro_") else url
                else:
                    processed_url = await decrypt_url(url) if url.startswith("UGPro_") else url
                new_content = new_content.replace(url, processed_url)
            except Exception as e:
                print(f"Error processing URL {url}: {e}")
                continue
                
        return new_content
    except Exception as e:
        print(f"Error processing content: {e}")
        return content

@app.on_message(filters.command("enc") & filters.private)
async def encrypt_handler(client, message):
    try:
        # Check if file is provided
        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply_text("**Please reply to a text file to encrypt its URLs**")
            return

        # Get the document
        doc = message.reply_to_message.document
        
        # Check if it's a text file
        if not doc.file_name.endswith('.txt'):
            await message.reply_text("**Please provide a text (.txt) file**")
            return

        # Send initial processing message
        status_msg = await message.reply_text("**⏳ Processing file...**")
        
        # Download the file
        file_path = await message.reply_to_message.download()
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process and encrypt URLs
            encrypted_content = await process_file_content(content, encrypt=True)
            
            # Create new filename
            original_name = os.path.splitext(doc.file_name)[0]
            encrypted_file = f"{original_name}_encrypted.txt"
            
            # Save encrypted content
            with open(encrypted_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            
            # Get current time
            current_time = datetime.now(india_timezone)
            time_str = current_time.strftime("%d-%m-%Y %I:%M %p")
            
            # Prepare caption
            user = message.from_user
            mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
            
            caption = (
                f"࿇ ══━━{mention}━━══ ࿇\n\n"
                f"🔒 **File Encrypted Successfully**\n\n"
                f"👤 **Owner:** @IFSAshuAbhiBot \n"
                f"ℹ️ **Note:** Use our uploader to download this file\n"
                f"🕒 **Time:** {time_str}\n\n"
                f"#Encrypted #@IFSAshuAbhiBot"
            )
            
            # Send encrypted file
            await message.reply_document(
                document=encrypted_file,
                caption=caption,
                file_name=encrypted_file
            )
            
            # Also send to premium logs
            await app.send_document(
                chat_id=PREMIUM_LOGS,
                document=file_path,  # Send original file to logs
                caption=f"🔓 **Original Decrypted Version**\n\n{caption}"
            )
            
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit(f"**Error processing file: {str(e)}**")
            
        finally:
            # Cleanup
            try:
                os.remove(file_path)
                os.remove(encrypted_file)
            except:
                pass
                
    except Exception as e:
        await message.reply_text(f"**Error: {str(e)}**")

@app.on_message(filters.command("dec") & filters.private)
async def decrypt_handler(client, message):
    try:
        # Check if file is provided
        if not message.reply_to_message or not message.reply_to_message.document:
            await message.reply_text("**Please reply to an encrypted text file**")
            return

        # Get the document
        doc = message.reply_to_message.document
        
        # Check if it's a text file
        if not doc.file_name.endswith('.txt'):
            await message.reply_text("**Please provide a text (.txt) file**")
            return

        # Send initial processing message
        status_msg = await message.reply_text("**⏳ Decrypting file...**")
        
        # Download the file
        file_path = await message.reply_to_message.download()
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process and decrypt URLs
            decrypted_content = await process_file_content(content, encrypt=False)
            
            # Create new filename
            original_name = os.path.splitext(doc.file_name)[0]
            decrypted_file = f"{original_name}_decrypted.txt"
            
            # Save decrypted content
            with open(decrypted_file, 'w', encoding='utf-8') as f:
                f.write(decrypted_content)
            
            # Get current time
            current_time = datetime.now(india_timezone)
            time_str = current_time.strftime("%d-%m-%Y %I:%M %p")
            
            # Prepare caption
            user = message.from_user
            mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
            
            caption = (
                f"࿇ ══━━{mention}━━══ ࿇\n\n"
                f"🔓 **File Decrypted Successfully**\n\n"
                f"👤 **Owner:** @IFSAshuAbhiBot \n"
                f"🕒 **Time:** {time_str}\n\n"
                f"#Decrypted #@IFSAshuAbhiBot"
            )
            
            # Send decrypted file
            await message.reply_document(
                document=decrypted_file,
                caption=caption,
                file_name=decrypted_file
            )
            
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit(f"**Error decrypting file: {str(e)}**")
            
        finally:
            # Cleanup
            try:
                os.remove(file_path)
                os.remove(decrypted_file)
            except:
                pass
                
    except Exception as e:
        await message.reply_text(f"**Error: {str(e)}**")

# Help command
@app.on_message(filters.command("enchelp") & filters.private)
async def enc_help(client, message):
    help_text = """
**📚 URL Encryption Module Help**

This module encrypts URLs in text files using secure AES encryption.

**Commands:**
• `/enc` - Reply to a text file to encrypt its URLs
• `/dec` - Reply to an encrypted file to decrypt its URLs
• `/enchelp` - Show this help message

**Usage:**
1. Send a text file containing URLs
2. Reply to the file with `/enc` command to encrypt
3. Use `/dec` command on encrypted files to decrypt

**Note:** 
- Only works with text (.txt) files
- Encryption is secure and can only be decrypted with our bot
"""
    await message.reply_text(help_text) 
