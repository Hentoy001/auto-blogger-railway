import os
import random
import requests
from io import BytesIO
from datetime import datetime, time as dt_time
from PIL import Image
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import time

# -------------------------
# CONFIG
# -------------------------
BLOGGER_BLOG_ID = os.environ.get("BLOGGER_BLOG_ID")
CREDENTIALS_FILE = "credentials.json"
API_KEY = os.environ.get("API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

TOPICS = [
    "lifestyle","history","wildlife","nature","politics",
    "religion","culture","taboos","tech","news",
    "crypto","AI","money-making ideas","apps history",
    "product knowledge","historical figures","celebrities"
]

POST_TIMES = [dt_time(10, 0), dt_time(16, 0)]
POST_LOG = "posted_topics.json"

genai.configure(api_key=API_KEY)

# -------------------------
# HELPERS
# -------------------------
def generate_blog(topic):
    return genai.generate_text(
        model="gemini-2.5-pro",
        prompt=f"Write a very detailed, professional, SEO-friendly blog article on: {topic}",
        max_output_tokens=4000
    ).output_text

def generate_meta_keywords(blog_text):
    meta = genai.generate_text(
        model="gemini-2.5-pro",
        prompt=f"Create a short meta description under 160 chars for this blog:\n{blog_text}",
        max_output_tokens=50
    ).output_text.strip()
    keywords = genai.generate_text(
        model="gemini-2.5-pro",
        prompt=f"Extract 10-15 SEO keywords/tags, separated by commas:\n{blog_text}",
        max_output_tokens=50
    ).output_text.strip()
    return meta, keywords

def generate_image(topic):
    img_resp = genai.generate_image(model="gemini-2.5-image", prompt=topic, size="1024x1024")
    image_url = img_resp.images[0].uri
    image_data = requests.get(image_url).content
    return Image.open(BytesIO(image_data))

def upload_image_to_imgbb(image: Image):
    buf = BytesIO()
    image.save(buf, format="PNG")
    r = requests.post(
        "https://api.imgbb.com/1/upload",
        files={"image": buf.getvalue()},
        data={"key": IMGBB_API_KEY}
    )
    data = r.json()
    if data["success"]: return data["data"]["url"]
    raise Exception("Image upload failed")

def publish(title, content, img_url=None, meta="", keywords=""):
    creds = Credentials.from_authorized_user_file(
        CREDENTIALS_FILE, ["https://www.googleapis.com/auth/blogger"]
    )
    service = build("blogger", "v3", credentials=creds)
    if img_url: content = f'<img src="{img_url}">\n{content}'
    post = {
        "kind": "blogger#post",
        "blog": {"id": BLOGGER_BLOG_ID},
        "title": title,
        "content": content,
        "labels": [kw.strip() for kw in keywords.split(",")],
        "customMetaData": f"<meta name='description' content='{meta}'>"
    }
    service.posts().insert(blogId=BLOGGER_BLOG_ID, body=post, isDraft=False).execute()
    print(f"[{datetime.now()}] Published: {title}")

def load_log(): return json.load(open(POST_LOG)) if os.path.exists(POST_LOG) else []
def save_log(log): json.dump(log, open(POST_LOG,"w"))

# -------------------------
# MAIN LOOP
# -------------------------
posted_topics = load_log()

while True:
    now = datetime.now()
    for scheduled in POST_TIMES:
        if now.hour == scheduled.hour and now.minute == scheduled.minute:
            remaining = [t for t in TOPICS if t not in posted_topics]
            if not remaining: posted_topics=[]
            topic = random.choice(remaining)
            print(f"[{now}] Generating blog: {topic}")
            blog = generate_blog(topic)
            meta, keywords = generate_meta_keywords(blog)
            img = generate_image(topic)
            img_url = upload_image_to_imgbb(img)
            publish(f"All About {topic.title()}", blog, img_url, meta, keywords)
            posted_topics.append(topic)
            save_log(posted_topics)
            time.sleep(60)  # prevent double-post in same minute
    time.sleep(30)
