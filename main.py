from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import lifespan
from routes.posts import post_router
from routes.search import search_router
from routes.image import image_router


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(post_router, prefix="/api/v1/posts", tags=["Posts"])
app.include_router(image_router, prefix="/api/v1/image", tags=["Image"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])


@app.get("/")
async def root():
    return {"message": "Welcome to FindMyMeow API"}
