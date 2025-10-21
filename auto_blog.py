import os
import time
import random
import json
from datetime import datetime, timedelta
from google.generativeai import Client
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# --- Environment Variables ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
BLOGGER_BLOG_ID = os.environ.get("BLOGGER_BLOG_ID")
API_KEY = os.environ.get("API_KEY")  # Gemini AI Key

# --- Blogger Setup ---
creds = {
    "installed": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:wg:2.0:oob","http://localhost"]
    }
}
scopes = ["https://www.googleapis.com/auth/blogger"]
credentials = Credentials.from_authorized_user_info(info=creds, scopes=scopes)
blogger_service = build("blogger", "v3", credentials=credentials)

# --- Gemini AI Client ---
client = Client(api_key=API_KEY)

# --- Topics Pool (wide coverage) ---
topics_pool = [
    "lifestyle", "technology", "history", "wildlife", "culture", "science",
    "finance", "health", "politics", "religion", "taboos", "apps", "crypto",
    "AI", "product knowledge", "historical figures", "celebrities", "nature",
    "space", "travel", "education", "environment", "movies", "music"
]

# --- Track topics posted in last 30 days ---
posted_topics_file = "posted_topics.json"
if os.path.exists(posted_topics_file):
    with open(posted_topics_file, "r") as f:
        posted_topics = json.load(f)
else:
    posted_topics = {}

# --- Posting Schedule (3–5 posts/day random times) ---
POST_TIMES = ["10:00", "13:00", "16:00", "19:00", "22:00"]

# --- Helper Functions ---
def save_posted_topics():
    with open(posted_topics_file, "w") as f:
        json.dump(posted_topics, f)

def generate_blog(topic):
    prompt = (
        f"Write a VERY detailed professional blog about '{topic}' with over 7000 words. "
        f"Include: catchy SEO title, meta description, SEO tags, headings, subheadings, "
        f"bullet points, examples, and make it suitable for Blogger. Return HTML content."
    )
    response = client.generate_content(prompt)
    return response.text

def generate_image(description):
    prompt = f"Create a high-quality image for: {description}"
    response = client.generate_content(prompt)
    try:
        image_base64 = response.image_base64
        return f"data:image/png;base64,{image_base64}"
    except AttributeError:
        return ""

def post_to_blogger(title, content):
    post = {"kind": "blogger#post", "title": title, "content": content}
    blogger_service.posts().insert(blogId=BLOGGER_BLOG_ID, body=post).execute()

def pick_topic():
    today = datetime.now().date()
    available_topics = [t for t in topics_pool if t not in posted_topics or 
                        (datetime.fromisoformat(posted_topics[t]) + timedelta(days=30)).date() < today]
    if not available_topics:
        posted_topics.clear()
        available_topics = topics_pool.copy()
    topic = random.choice(available_topics)
    posted_topics[topic] = datetime.now().isoformat()
    save_posted_topics()
    return topic

# --- Main Loop ---
while True:
    now = datetime.now().strftime("%H:%M")
    if now in POST_TIMES:
        topic = pick_topic()
        print(f"Generating blog for topic: {topic}")

        # Generate blog content
        blog_html = generate_blog(topic)

        # Generate 1–2 images
        img_tags = ""
        for _ in range(random.randint(1,2)):
            img_tags += f"<br><img src='{generate_image(f'Image for {topic}')}'/>"
        blog_html += img_tags

        # Fallback title
        title_line = blog_html.split("\n")[0][:70]
        post_to_blogger(title_line, blog_html)

        print(f"Blog posted for topic: {topic}")
        time.sleep(60)
    time.sleep(30)
