import asyncio
from datetime import datetime
from pyrogram.errors import UserNotParticipant
from pyrogram.types import *
from config import CHANNEL_ID2
from Extractor.core import script
from Extractor.core.mongo.plans_db import premium_users


async def chk_user(query, user_id):
    user = await premium_users()
    if user_id in user:
        await query.answer("Premium User!!")
        return 0
    else:
        await query.answer("Sir, you don't have premium access!!", show_alert=True)
        return 1


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""

        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1

        unit = ts[index:].lstrip()

        if value:
            value = int(value)

        return value, unit

    value, unit = extract_value_and_unit(time_string.lower())

    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


async def subscribe(app, message):
    try:
        update_channel = CHANNEL_ID2
        if not update_channel:
            return 0

        try:
            user = await app.get_chat_member(update_channel, message.from_user.id)
            if user.status == "kicked":
                await message.reply_text("🚫 Sorry Sir, You are Banned. Contact My Support Group @saini_sahab_19")
                return 1
        except UserNotParticipant:
            try:
                # 1. Create approval-based invite link
                invite = await app.create_chat_invite_link(
                    chat_id=update_channel,
                    name=f"JoinRequest-{message.from_user.id}-{datetime.now().isoformat()}",
                    creates_join_request=True
                )
                link = invite.invite_link

                # 2. Send the invite message
                sent = await message.reply_photo(
                    photo="https://i.ibb.co/qYszKKFN/arafed-warrior-standing-front-mountain-with-sword-generative-ai-955925-50481.jpg",
                    caption=script.FORCE_MSG.format(message.from_user.mention),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🤖 ɴᴇᴇᴅ ᴀᴘᴘʀᴏᴠᴀʟ ᴛᴏ ᴊᴏɪɴ 🤖", url=link)
                    ]])
                )

                # 3. Wait 15 seconds
                await asyncio.sleep(15)

                # 4. Revoke the invite link
                await app.revoke_chat_invite_link(update_channel, invite.invite_link)

                # 5. Delete the invite message
                await sent.delete()

                # 6. Send timeout message
                await message.reply_animation(
                    animation="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcGxsMjVoaWt3cTJqcDJtZXg2cXFrdjBqOGZ6b25zNWp6c2J3aDg4aCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/O4PNDmchDN81Nr4Xib/giphy.gif",
                    caption="🕒 ᴛɪᴍᴇᴏᴜᴛ ᴇxᴘɪʀᴇᴅ!\n\nᴘʟᴇᴀsᴇ ᴜsᴇ /start ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ɪɴᴠɪᴛᴇ ʟɪɴᴋ.",
                )

            except Exception as e:
                print(f"Link generation failed: {e}")
                await message.reply_text(
                    "❗ Please join our updates channel to use the bot.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🤖 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 🤖", url="https://t.me/nothing_saini")
                    ]])
                )
            return 1

        except Exception as e:
            print(f"Subscribe error inner: {e}")
            return 0

        return 0

    except Exception as e:
        print(f"Subscribe error outer: {e}")
        return 0
