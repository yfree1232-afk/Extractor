import asyncio
import traceback
from pyrogram import filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from config import OWNER_ID
from Extractor import app
from Extractor.core.mongo.usersdb import get_users



# ---------------------------------------------------------------- #

async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        return 400, f"{user_id} : deactivated\n"
    except UserIsBlocked:
        return 400, f"{user_id} : blocked the bot\n"
    except PeerIdInvalid:
        return 400, f"{user_id} : user id invalid\n"
    except Exception as e:
        return 500, f"{user_id} : {str(e)}\n"
    

# ----------------------------Broadcast---------------------------- #
    
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(_, message):
    if not message.reply_to_message:
        await message.reply_text(
            "❌ <b>Error:</b> Reply to a message to broadcast it."
        )
        return    
    
    exmsg = await message.reply_text(
        "🔄 <b>Broadcasting Started</b>\n\n"
        "Please wait while I send the message to all users..."
    )
    
    all_users = await get_users()
    if not all_users:
        await exmsg.edit_text("❌ No users found in database!")
        return
        
    done_users = 0
    failed_users = 0
    failed_details = ""
    
    for user in all_users:
        status, error = await send_msg(user, message.reply_to_message)
        if status == 200:
            done_users += 1
        else:
            failed_users += 1
            if error:
                failed_details += error
        await asyncio.sleep(0.1)
    
    broadcast_text = (
        "📊 <b>Broadcast Completed</b>\n\n"
        f"✅ Success: <code>{done_users}</code> users\n"
        f"❌ Failed: <code>{failed_users}</code> users\n\n"
    )
    
    if failed_users > 0:
        broadcast_text += (
            "<b>Failure Details:</b>\n"
            f"<code>{failed_details[:1000]}</code>"  # Limit details to 1000 chars
        )
    
    await exmsg.edit_text(broadcast_text)

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def forward_broadcast(_, message):
    if not message.reply_to_message:
        await message.reply_text(
            "❌ <b>Error:</b> Reply to a message to forward broadcast it."
        )
        return
        
    exmsg = await message.reply_text(
        "🔄 <b>Forward Broadcasting Started</b>\n\n"
        "Please wait while I forward the message to all users..."
    )
    
    users = await get_users()
    if not users:
        await exmsg.edit_text("❌ No users found in database!")
        return
        
    done_users = 0
    failed_users = 0
    
    for user in users:
        try:
            await message.reply_to_message.forward(int(user))
            done_users += 1
        except Exception:
            failed_users += 1
        await asyncio.sleep(0.1)
    
    await exmsg.edit_text(
        "📊 <b>Forward Broadcast Completed</b>\n\n"
        f"✅ Success: <code>{done_users}</code> users\n"
        f"❌ Failed: <code>{failed_users}</code> users"
    )


# ----------------------------Announce---------------------------- #
        
@app.on_message(filters.command("announce") & filters.user(OWNER_ID))
async def announced(_, message):
    if message.reply_to_message:
      to_send=message.reply_to_message.id
    if not message.reply_to_message:
      return await message.reply_text("Reply To Some Post To Broadcast")
    users = await get_users() or []
    print(users)
    failed_user = 0
  
    for user in users:
      try:
        await _.forward_messages(chat_id=int(user), from_chat_id=message.chat.id, message_ids=to_send)
        await asyncio.sleep(1)
      except Exception as e:
        failed_user += 1
          
    if failed_users == 0:
        await exmsg.edit_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{done_users}` **ᴜsᴇʀs**",
        )
    else:
        await exmsg.edit_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{done_users}` **ᴜsᴇʀs**\n\n**ɴᴏᴛᴇ:-** `ᴅᴜᴇ ᴛᴏ sᴏᴍᴇ ɪssᴜᴇ ᴄᴀɴ'ᴛ ᴀʙʟᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ` `{failed_users}` **ᴜsᴇʀs**",
        )




