from pyrogram import filters
import json
import os
from Extractor import app
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
from Extractor.core.utils import forward_to_log

# Command handler
@app.on_message(filters.command("getapi"))
async def handle_getapi_command(client, message):
    await findapis_extract(client, message)

# Callback query handler for findapi button
@app.on_callback_query(filters.regex("^findapi_"))
async def handle_findapi_callback(client, callback_query: CallbackQuery):
    try:
        # Answer callback query immediately to prevent timeout
        await callback_query.answer()
        
        # Ask user for input with clear instructions
        msg = await callback_query.message.reply_text(
            "**🔍 Enter App Name To Search**\n\n"
            "• Type the name of the app you want to search\n"
            "• You have 60 seconds to respond\n"
            "• Press /cancel to cancel the search"
        )
        
        # Wait for user response with shorter timeout
        try:
            response = await client.listen(
                chat_id=callback_query.message.chat.id,
                filters=filters.text & filters.user(callback_query.from_user.id) & ~filters.command("cancel"),
                timeout=60  # Reduced to 60 seconds
            )
            
            if not response or not response.text:
                await msg.edit_text("**❌ No input received. Please try again using /getapi**")
                return
                
            search_term = response.text.lower()
            
            # Delete the response message
            try:
                await response.delete()
            except:
                pass  # Ignore if message delete fails
            
        except asyncio.TimeoutError:
            await msg.edit_text(
                "**⏰ Search timeout!**\n\n"
                "• The search timed out after 60 seconds\n"
                "• Please try again using /getapi"
            )
            return
        except Exception as e:
            await msg.edit_text(
                "**❌ An error occurred**\n\n"
                "• Please try again using /getapi\n"
                f"• Error: `{str(e)}`"
            )
            return
            
        # Show searching message
        await msg.edit_text("**🔍 Searching...**")
            
        # Check if file exists
        if not os.path.exists('appxapis.json'):
            await msg.edit_text(
                "**❌ Database Error**\n\n"
                "• The API database file was not found\n"
                "• Please contact an administrator"
            )
            return
        
        # Load and search through the JSON file
        try:
            with open('appxapis.json', 'r', encoding='utf-8') as f:
                apps = json.load(f)
        except Exception as e:
            await msg.edit_text(
                "**❌ Database Error**\n\n"
                "• Could not read the API database\n"
                "• Please contact an administrator"
            )
            return
        
        # Search for matches (case insensitive)
        matches = []
        for app in apps:
            if search_term in app['name'].lower():
                matches.append(app)
        
        if not matches:
            await msg.edit_text(
                "**❌ No Results Found**\n\n"
                f"• No apps found matching '{search_term}'\n"
                "• Try searching with a different name\n"
                "• Use /getapi to search again"
            )
            return
        
        # Create result text with found apps
        result_text = f"**🔍 Found {len(matches)} Apps:**\n\n"
        keyboard = []
        row = []
        
        for idx, app in enumerate(matches, 1):
            name = app['name']
            api = app['api']
            # Add to text
            result_text += f"**{idx}. {name}**\n`{api}`\n\n"
            
            # Create button
            button = InlineKeyboardButton(
                f"👑 {name}",
                callback_data=f"appx_{api}"  # Changed to appx_ to match other callbacks
            )
            row.append(button)
            
            # 2 buttons per row
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« 𝐁𝐚𝐜𝐤 »", callback_data="home_")])
        
        # Send the results
        await msg.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
       
    except Exception as e:
        print(f"Error in findapi callback: {e}")
        try:
            await callback_query.message.reply_text(
                "**❌ Error Occurred**\n\n"
                "• Something went wrong while processing your request\n"
                "• Please try again using /getapi"
            )
        except:
            pass

async def findapis_extract(client, message):
    try:
        # Ask user for input with clear instructions
        msg = await message.reply_text(
            "**🔍 Enter App Name To Search**\n\n"
            "• Type the name of the app you want to search\n"
            "• You have 60 seconds to respond\n"
            "• Press /cancel to cancel the search"
        )
        
        # Wait for user response
        try:
            response = await client.listen(
                chat_id=message.chat.id,
                filters=filters.text & filters.user(message.from_user.id) & ~filters.command("cancel"),
                timeout=60  # 60 seconds timeout
            )
            
            if not response or not response.text:
                await msg.edit_text("**❌ No input received. Please try again.**")
                return
                
            search_term = response.text.lower()
            
            # Delete the response message
            try:
                await response.delete()
            except:
                pass  # Ignore if message delete fails
            
        except asyncio.TimeoutError:
            await msg.edit_text(
                "**⏰ Search timeout!**\n\n"
                "• The search timed out after 60 seconds\n"
                "• Please try again using /getapi"
            )
            return
        except Exception as e:
            await msg.edit_text(
                "**❌ An error occurred**\n\n"
                "• Please try again using /getapi\n"
                f"• Error: `{str(e)}`"
            )
            return
            
        # Show searching message
        await msg.edit_text("**🔍 Searching...**")
            
        # Check if file exists
        if not os.path.exists('appxapis.json'):
            await msg.edit_text(
                "**❌ Database Error**\n\n"
                "• The API database file was not found\n"
                "• Please contact an administrator"
            )
            return
        
        # Load and search through the JSON file
        try:
            with open('appxapis.json', 'r', encoding='utf-8') as f:
                apps = json.load(f)
        except Exception as e:
            await msg.edit_text(
                "**❌ Database Error**\n\n"
                "• Could not read the API database\n"
                "• Please contact an administrator"
            )
            return
        
        # Search for matches (case insensitive)
        matches = []
        for app in apps:
            if search_term in app['name'].lower():
                matches.append(app)
        
        if not matches:
            await msg.edit_text(
                "**❌ No Results Found**\n\n"
                f"• No apps found matching '{search_term}'\n"
                "• Try searching with a different name\n"
                "• Use /getapi to search again"
            )
            return
        
        # Create result text with found apps
        result_text = f"**🔍 Found {len(matches)} Apps:**\n\n"
        keyboard = []
        row = []
        
        for idx, app in enumerate(matches, 1):
            name = app['name']
            api = app['api']
            # Add to text
            result_text += f"**{idx}. {name}**\n`{api}`\n\n"
            
            # Create button
            button = InlineKeyboardButton(
                f"👑 {name}",
                callback_data=f"appx_{api}"
            )
            row.append(button)
            
            # 2 buttons per row
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« 𝐁𝐚𝐜𝐤 »", callback_data="home_")])
        
        # Send the results
        await msg.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
       
    except Exception as e:
        print(f"Error in findapis_extract: {e}")
        try:
            await message.reply_text(
                "**❌ Error Occurred**\n\n"
                "• Something went wrong while processing your request\n"
                "• Please try again using /getapi"
            )
        except:
            pass

def find_api(keyword, data):
    matching_results = [
        f"<b><blockquote>{item['name']}</blockquote></b>\n<code>{item['api']}</code>\n\n"
        for idx, item in enumerate(data) 
        if keyword.lower() in item['name'].lower()
    ]
    
    if matching_results:
        return f"Found <b>{len(matching_results)} result(s)</b> for your search term '{keyword}':\n\n" + "\n".join(matching_results)
    else:
        return f"No result found for your search term '{keyword}'"
        
