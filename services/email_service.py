import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from core.database import db
from pathlib import Path
from datetime import datetime
from pytz import timezone

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

print("EMAIL_ADDRESS from env:", EMAIL_ADDRESS)


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

    print(f"📬 Found {len(posts_to_notify)} posts to notify.")

    for post in posts_to_notify:
        try:
            subject = "แจ้งเตือน: พบแมวที่คุณอาจกำลังตามหา"
            body_plain = (
                f"มีโพสต์ใหม่เกี่ยวกับแมวที่คุณกำลังตามหา:\n\n"
                f"ชื่อแมว: {post.get('cat_name', '-')}\n"
                f"เพศ: {post.get('gender', '-')}\n"
                f"สี: {post.get('color', '-')}\n"
                f"สายพันธุ์: {post.get('breed', '-')}\n"
                f"สถานที่: แขวง{post['location'].get('sub_district', '')} "
                f"เขต{post['location'].get('district', '')} จังหวัด{post['location'].get('province', '')}\n\n"
                f"ขอบคุณที่ใช้ FindMyMeow ❤️"
            )

            body_html = f"""
            <html>
              <body style="font-family:sans-serif; color:#333;">
                <h2>🐾 มีโพสต์ใหม่เกี่ยวกับแมวที่คุณกำลังตามหา:</h2>
                <ul>
                  <li><strong>ชื่อแมว:</strong> {post.get('cat_name', '-')}</li>
                  <li><strong>เพศ:</strong> {post.get('gender', '-')}</li>
                  <li><strong>สี:</strong> {post.get('color', '-')}</li>
                  <li><strong>สายพันธุ์:</strong> {post.get('breed', '-')}</li>
                  <li><strong>สถานที่:</strong> แขวง{post['location'].get('sub_district', '')}, 
                      เขต{post['location'].get('district', '')}, จังหวัด{post['location'].get('province', '')}</li>
                </ul>
                <p>ขอบคุณที่ใช้ <strong>FindMyMeow</strong> ❤️</p>
              </body>
            </html>
            """

            user_email = post.get("user_email")
            if user_email:
                send_email('kulisara2908@gmail.com', subject, body_plain, body_html)
            else:
                print("⚠️ Missing user_email for post:", post.get("post_id", "unknown"))

        except Exception as e:
            print(f"❌ Failed to send email for post {post.get('post_id', 'unknown')}: {e}")

    print("✅ Finished sending notifications:", datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S"))
