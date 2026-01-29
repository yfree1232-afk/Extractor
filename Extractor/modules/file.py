from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

@Client.on_message(filters.command(["rgvikramjeet"]))
async def rgvikramjeet(bot: Client, m: Message):
    await m.reply_text("Send **ID & Password** like this: `ID*Password`")

    input1: Message = await bot.listen(m.chat.id)
    raw_text = input1.text
    userid = raw_text.split("*")[0]
    password = raw_text.split("*")[1]

    login_url = "https://appapi.videocrypt.in/data_model/users/login_auth"
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "Origin": "https://rankersgurukul.com",
        "Referer": "https://rankersgurukul.com/",
        "Appid": "753",
        "Devicetype": "4",
        "Lang": "1"
    }
    payload = {
        "userid": userid,
        "password": password
    }

    try:
        response = requests.post(login_url, headers=headers, json=payload)
        data = response.json()

        if "access_token" not in data:
            await m.reply_text("❌ Login failed. Please check your ID and password.")
            return

        token = data["access_token"]
        user_id = data.get("user_id") or data.get("userid")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Get courses
        courses_url = f"https://appapi.videocrypt.in/data_model/courses?userId={user_id}"
        res_courses = requests.get(courses_url, headers=auth_headers)
        courses = res_courses.json().get("data", [])

        if not courses:
            await m.reply_text("⚠️ No courses found.")
            return

        message_text = "**📚 Your Courses:**\n\n"
        for course in courses:
            course_id = course.get("id")
            course_name = course.get("course_name") or course.get("name")
            message_text += f"`{course_id}` - **{course_name}**\n"
        await m.reply_text(message_text)

        # Ask for course ID
        await m.reply_text("Send the **Course ID** to continue:")
        input2 = await bot.listen(m.chat.id)
        selected_course = input2.text.strip()

        # Get subjects
        subjects_url = f"https://appapi.videocrypt.in/data_model/courses/subjects?courseId={selected_course}"
        res_subjects = requests.get(subjects_url, headers=auth_headers)
        subjects = res_subjects.json().get("data", [])

        subj_text = "**📘 Subjects:**\n\n"
        for subj in subjects:
            subj_id = subj.get("id")
            subj_name = subj.get("subject_name")
            subj_text += f"`{subj_id}` - **{subj_name}**\n"
        await m.reply_text(subj_text)

        # Ask for subject ID
        await m.reply_text("Send the **Subject ID**:")
        input3 = await bot.listen(m.chat.id)
        selected_subject = input3.text.strip()

        # Get topics
        topics_url = f"https://appapi.videocrypt.in/data_model/courses/subjects/topics?subjectId={selected_subject}&courseId={selected_course}"
        res_topics = requests.get(topics_url, headers=auth_headers)
        topics = res_topics.json().get("data", [])

        topic_text = "**📝 Topics:**\n\n"
        for topic in topics:
            topic_id = topic.get("id")
            topic_name = topic.get("topic_name")
            topic_text += f"`{topic_id}` - **{topic_name}**\n"
        await m.reply_text(topic_text)

        # Ask for topic ID(s)
        await m.reply_text("Send one or more **Topic IDs** (separated by &):")
        input4 = await bot.listen(m.chat.id)
        topic_ids = input4.text.strip().split("&")

        # Ask for resolution (if needed)
        await m.reply_text("Now send the **Resolution** (or type 'any'):")
        input5 = await bot.listen(m.chat.id)
        resolution = input5.text.strip()

        download_links = []
        for topic_id in topic_ids:
            video_url = f"https://appapi.videocrypt.in/data_model/courses/videos?topicId={topic_id}&courseId={selected_course}"
            res_videos = requests.get(video_url, headers=auth_headers)
            videos = res_videos.json().get("data", [])
            for video in videos:
                title = video.get("Title")
                enc_link = video.get("download_link") or video.get("pdf_link")
                if enc_link:
                    try:
                        key = "638udh3829162018".encode("utf8")
                        iv = "fedcba9876543210".encode("utf8")
                        ciphertext = bytearray.fromhex(b64decode(enc_link.encode()).hex())
                        cipher = AES.new(key, AES.MODE_CBC, iv)
                        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
                        decrypted_link = plaintext.decode('utf-8')
                        download_links.append(f"{title}: {decrypted_link}")
                    except Exception as e:
                        download_links.append(f"{title}: Failed to decrypt")

        filename = f"Rgvikramjeet_{selected_course}.txt"
        with open(filename, 'w') as f:
            for line in download_links:
                f.write(f"{line}\n")

        await m.reply_document(filename)
        await m.reply_text("✅ Done")

    except Exception as e:
        await m.reply_text(f"❌ Error occurred: {e}")
