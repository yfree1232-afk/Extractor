import re
import json
import urllib.parse
import requests
from Extractor import app

async def jchemistry(app, message):
    input1 = await app.ask(message.chat.id, text="Send **ID & Password** in this manner, otherwise, the bot will not respond.\n\nSend like this: **ID*Password**")
    raw_text = input1.text
    ph, pas = raw_text.split("*")
    await input1.delete(True)
    
    url = 'https://jchemistry-api.edmingle.com/nuSource/api/v1/tutor/login'
    
    payload = {
        "username": ph,
        "password": pas,
        "persistent_login": True
    }
    data = {"JSONString": json.dumps(payload)}
    
    try:
        r = requests.post(url, data=data).json()
        
        if r.get("message") != "Login successful":
            await message.reply_text(f"Login Failed! Error: {r.get('message', 'Invalid Credentials')}")
            return
            
        token = r.get("user", {}).get("apikey")
        org_id = r.get("user", {}).get("organization_id")
        
        headers = {
            "APIKEY": token,
            "ORGID": str(org_id)
        }
        
        await message.reply_text(f"Login Successful! Auth: `{token}`\nOrgID: `{org_id}`")
        
    except Exception as e:
        await message.reply_text(f"Error during login: {str(e)}")
