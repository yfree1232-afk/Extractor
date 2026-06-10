import re
import requests
import urllib.parse
from Extractor import app

async def jchemistry(app, message):
    await message.reply_text("Currently J Chemistry requires an org code.\nPlease use the **🎯 CʟᴀssPʟᴜs 🎯** button if you have it!")
