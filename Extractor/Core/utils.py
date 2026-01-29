from datetime import datetime
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from config import CHANNEL_ID
from Extractor import app

async def forward_to_log(message: Message, module_name: str):
    """Forward user messages to log channel with module info"""
    try:
        # Remove the minus sign from the channel ID if present
        channel_id = str(CHANNEL_ID).replace("-", "")
        
        log_text = "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        log_text += f"👤 {message.from_user.first_name}"
        if message.from_user.username:
            log_text += f" (@{message.from_user.username})"
        log_text += f" [{message.from_user.id}]\n\n"
        
        log_text += f"📱 Module: {module_name}\n"
        log_text += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
        
        log_text += f"💬 Message:\n`**{message.text}**`\n"
        log_text += "\n━━━━━━━━━━━━━━━━━━━━━━"

        try:
            # First try with original channel ID
            await app.send_message(
                chat_id=CHANNEL_ID,
                text=log_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e1:
            try:
                # If failed, try with -100 prefix
                await app.send_message(
                    chat_id=f"-100{channel_id}",
                    text=log_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e2:
                print(f"Error with original channel ID: {e1}")
                print(f"Error with modified channel ID: {e2}")
                print(f"Channel ID attempted: {CHANNEL_ID} and -100{channel_id}")
                raise

    except Exception as e:
        print(f"Error forwarding to log channel: {e}")
        print(f"Message: {message.text if message.text else 'No text'}")
        print(f"From user: {message.from_user.first_name} [{message.from_user.id}]")
        print(f"Module: {module_name}")
        print(f"Channel ID: {CHANNEL_ID}") 