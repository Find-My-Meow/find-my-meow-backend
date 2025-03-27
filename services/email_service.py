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
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

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


async def send_daily_email_notifications():
    print("⏰ Running email notification job...")
    posts_to_notify = await db.database["posts_v2"].find(
        {"email_notification": True}
    ).to_list(length=100)
    for post in posts_to_notify:
        try:
            # Find similar posts for each post
            similar_posts, _ = await find_similar_posts_by_post_id(post["post_id"], radius_km=20)
            if similar_posts:
                # If similar posts are found, create a list of links to each post
                subject = "แจ้งเตือน: มีโพสต์ใหม่เกี่ยวกับแมวของคุณ"
                
                # Prepare plain text email body
                similar_posts_links = "\n".join(
                    [f"- {similar_post['cat_name'] if similar_post['cat_name'] else f'โพสต์ {index + 1}'} : http://localhost:5173/cat-detail/{similar_post['post_id']}"
                     for index, similar_post in enumerate(similar_posts)]
                )
                body_plain = (
                    f"มีโพสต์ใหม่เกี่ยวกับแมวของคุณ:\n\n"
                    f"โพสต์ที่คล้ายกัน:\n"
                    f"{similar_posts_links}\n\n"
                    f"หากคุณยังไม่พบแมวของคุณ, คุณสามารถลองค้นหาเพิ่มเติมได้ที่ "
                    f"FindMyMeow: http://localhost:5173/cat-detail/{post['post_id']}"
                )

                # Prepare HTML email body
                similar_posts_html = "".join(
                    [f'<p><a href="http://localhost:5173/cat-detail/{similar_post["post_id"]}">โพสต์ {index + 1}</a></p>'
                        for index, similar_post in enumerate(similar_posts)])

                body_html = f"""
                <html>
                  <body style="font-family:sans-serif; color:#333;">
                    <h2>🐾 มีโพสต์ใหม่เกี่ยวกับแมวของคุณ:</h2>
                    <p>โพสต์ที่คล้ายกัน:</p>
                    {similar_posts_html}
                    <p>หากคุณยังไม่พบแมวที่คุณกำลังตามหา, คุณสามารถลองค้นหาเพิ่มเติมได้ที่
                    <a href="http://localhost:5173/cat-detail/{post['post_id']}">FindMyMeow</a></p>
                  </body>
                </html>
                """

            else:
                print(f"⚠️ No similar posts found for post {post.get('post_id', 'unknown')}")
                
                # If no similar posts are found, suggest the general search URL
                subject = "แจ้งเตือน: ยังไม่พบโพสต์ที่คล้ายกับแมวของคุณ"
                body_plain = (
                    f"ขอโทษค่ะ, ยังไม่พบโพสต์ที่คล้ายกับแมวของคุณ:\n\n"
                    f"หากคุณยังไม่พบแมวที่คุณกำลังตามหา, คุณสามารถลองค้นหาเพิ่มเติมได้ที่ "
                    f"FindMyMeow: http://localhost:5173/search-cat\n\n"
                )

                body_html = f"""
               <html>
                <body style="font-family:sans-serif; color:#333;">
                    <h2>🐾 ขอโทษค่ะ, ยังไม่พบโพสต์ที่คล้ายกับแมวของคุณ:</h2>
                     <p>หากคุณยังไม่พบแมวที่คุณกำลังตามหา, คุณสามารถลองค้นหาเพิ่มเติมได้ที่
                     <a href="http://localhost:5173/search-cat">FindMyMeow</a></p>
                    </body>
                </html>
                """

            user_email = post.get("user_email")
            loop = asyncio.get_running_loop()
            if user_email:
                await loop.run_in_executor(None, send_email, user_email, subject, body_plain, body_html)

            else:
                print("⚠️ Missing user_email for post:", post.get("post_id", "unknown"))

        except Exception as e:
            print(f"❌ Failed to send email for post {post.get('post_id', 'unknown')}: {e}")

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
            print(f"✅ Email sent, waiting for the next day at 10:00 PM...")
            await asyncio.sleep(24 * 60 * 60)  # Wait for 24 hours (1 day) before sending again
        else:
            # Wait for 60 min before checking again
            await asyncio.sleep(60 * 60)


