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
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Origin': 'https://www.jchemistry.online',
        'Referer': 'https://www.jchemistry.online/',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    }
    payload = {
        'JSONString': json.dumps({
            'username': ph,
            'password': pas,
            'persistent_login': True,
            'device_type': 1,
            'server_key': '2c83aa73da07cf76461d6478c31b73bb',
            'device_key': '34d701830176de7d642b644825b210b5'
        })
    }
    data = urllib.parse.urlencode(payload)
    
    try:
        req = requests.post(url, data=data, headers=headers)
        r = req.json()
        if r.get('code') != 200:
            await message.reply_text(f"Login Failed! Error: {r.get('message', 'Invalid Credentials')}")
            return
            
        token = r.get('tutor', {}).get('auth_token')
        org_id = r.get('tutor', {}).get('org_id', 0)
        
        headers['APIKEY'] = token
        headers['ORGID'] = str(org_id)
        headers['ISKONNECT'] = '0'
        
        course_url = 'https://jchemistry-api.edmingle.com/nuSource/api/v1/tutor/get_all_batches'
        r2 = requests.get(course_url, headers=headers).json()
        
        await message.reply_text(f"Login Successful! Auth: `{token}`\nExtracted: {str(r2)[:100]}")
        
    except Exception as e:
        await message.reply_text(f"Error during login: {str(e)}")
