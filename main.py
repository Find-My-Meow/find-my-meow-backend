from fastapi import FastAPI
from database import lifespan
from routes.posts import post_router

app = FastAPI(lifespan=lifespan)

app.include_router(post_router, prefix="/api/v1/posts", tags=["Posts"])

@app.get("/")
async def root():
    return {"message": "Welcome to FindMyMeow API"}
