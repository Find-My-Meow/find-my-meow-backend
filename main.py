from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import lifespan
from routes.posts import post_router
from routes.search import search_router
from routes.image import image_router

import asyncio
from services.email_service import send_daily_email_notifications

app = FastAPI(lifespan=lifespan)

# 🛠️ Trigger the email function once on server start
@app.on_event("startup")
async def run_email_job_on_startup():
    print("🚀 Sending email notifications on startup...")
    asyncio.create_task(send_daily_email_notifications())

# 🛠️ Optional endpoint to trigger email manually
@app.get("/api/v1/trigger-email-now")
async def trigger_email_now():
    await send_daily_email_notifications()
    return {"message": "✅ Email notifications sent."}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routers
app.include_router(post_router, prefix="/api/v1/posts", tags=["Posts"])
app.include_router(image_router, prefix="/api/v1/image", tags=["Image"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": "Welcome to FindMyMeow API"}

