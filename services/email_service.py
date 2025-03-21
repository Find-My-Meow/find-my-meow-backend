import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from database import db

# Load environment variables
load_dotenv()

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email(recipient_email, subject, body):
    """
    Sends an email using Gmail SMTP.
    
    Args:
        recipient_email (str): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The email body content.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        
        print(f"Email sent to {recipient_email} successfully!")
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")

async def send_daily_email_notifications():
    # Query all posts where email_notification is True
    posts_to_notify = await db.posts.find({"email_notification": True}).to_list(length=100)

    # Loop through all posts and send email
    for post in posts_to_notify:
        subject = "Cat Found Post Notification"
        body = f"A post about a found cat has been created. \n\nDetails: \nCat Name: {post['cat_name']} \nGender: {post['gender']} \nColor: {post['color']} \nBreed: {post['breed']} \nLocation: {post['location']}"

        try:
            send_email(post['user_email'], subject, body)
        except Exception as e:
            print(f"Failed to send email to {post['user_email']}: {e}")
