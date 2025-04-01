import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from core.database import db
from pathlib import Path
from datetime import datetime
from pytz import timezone
from datetime import datetime
from pytz import timezone
import asyncio
from utils.search_utils import find_similar_posts_by_post_id
# Load environment
load_dotenv()

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL")

def send_email(recipient_email, subject, body_plain, body_html=None):
    """
    Sends an email using Gmail SMTP with plain text + optional HTML.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"FindMyMeow <{EMAIL_ADDRESS}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Reply-To"] = EMAIL_ADDRESS
        msg["X-Priority"] = "3"
        msg["X-Mailer"] = "FindMyMeow Mailer (Python)"
        msg["MIME-Version"] = "1.0"
        msg["Content-Type"] = "text/html; charset=UTF-8"


        msg.attach(MIMEText(body_plain, "plain"))

        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())

        print(f"✅ Email sent to {recipient_email} successfully!")
    except Exception as e:
        print(f"❌ Error sending email to {recipient_email}: {e}")


from collections import defaultdict

async def send_daily_email_notifications():
    print("⏰ Running email notification job...")
    posts_to_notify = await db.database["posts_v2"].find(
        {"email_notification": True}
    ).to_list(length=100)

    user_matches = defaultdict(list)

    for post in posts_to_notify:
        try:
            similar_posts, _ = await find_similar_posts_by_post_id(post["post_id"], radius_km=20)
            if similar_posts:
                user_email = post.get("user_email")
                if user_email:
                    user_matches[user_email].extend(similar_posts)
        except Exception as e:
            print(f"❌ Failed for post {post.get('post_id', 'unknown')}: {e}")

    for user_email, matched_posts in user_matches.items():
        try:
            subject = "แจ้งเตือน: มีโพสต์ใหม่เกี่ยวกับแมวของคุณ"
            similar_posts_links = "\n".join(
                [f"- {p['cat_name'] or f'โพสต์ {i+1}'}: {FRONTEND_URL}/cat-detail/{p['post_id']}" 
                 for i, p in enumerate(matched_posts)]
            )
            body_plain = (
                f"มีโพสต์ใหม่เกี่ยวกับแมวของคุณ:\n\n"
                f"{similar_posts_links}\n\n"
                f"ไปที่เว็บไซต์ FindMyMeow เพื่อติดตามเพิ่มเติม"
            )

            similar_posts_html = "".join(
                [f'<p><a href="{FRONTEND_URL}/cat-detail/{p["post_id"]}">โพสต์ {i+1}</a></p>' 
                 for i, p in enumerate(matched_posts)]
            )
            body_html = f"""
            <html>
              <body style="font-family:sans-serif; color:#333;">
                <h2>🐾 มีโพสต์ใหม่เกี่ยวกับแมวของคุณ:</h2>
                {similar_posts_html}
                <p>ดูเพิ่มเติมได้ที่ <a href="{FRONTEND_URL}">FindMyMeow</a></p>
              </body>
            </html>
            """

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, send_email, user_email, subject, body_plain, body_html)

        except Exception as e:
            print(f"❌ Failed to send to {user_email}: {e}")

    print("✅ Finished sending notifications:", datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S"))

async def run_email_every_11_AM(send_function):
    tz = timezone("Asia/Bangkok")

    while True:
        now = datetime.now(tz)

        # Print the current time for debugging
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check if it's exactly 11:00 AM 
        if now.hour == 11:
            print(f"✅ Sending email at {now.strftime('%H:%M:%S')}")
            await send_function()
            print(f"✅ Email sent, waiting for the next day at 11:00 AM...")
            await asyncio.sleep(24 * 60 * 60)  # Wait for 24 hours (1 day) before sending again
        else:
            # Wait for 60 min before checking again
            await asyncio.sleep(60 * 60)


