import io
import pytest
import numpy as np
from PIL import Image as PILImage
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from routes.search import search_router
from core import database as db_module


app = FastAPI()
app.include_router(search_router, prefix="/api/v1/search")


@pytest.mark.asyncio
async def test_search_with_image(monkeypatch, tmp_path):
    # Create a dummy image in memory
    dummy_img = PILImage.new("RGB", (224, 224), color="gray")
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    buf.seek(0)

    # Mock detection
    monkeypatch.setattr("routes.search.detect_cats",
                        lambda img: [[0, 0, 100, 100]])
    # cat crop
    monkeypatch.setattr("routes.search.crop_cats", lambda img, det: [img])
    # extract feature
    monkeypatch.setattr("routes.search.extract_cat_features",
                        lambda crops: [[[0.1]*512]])

    # Mock FAISS index
    class DummyFaissIndex:
        def __init__(self):
            self.ntotal = 1  # 1 vector

        def search(self, x, k):
            distances = np.array([[42.0]])
            ids = np.array([[401]])  # image_id = 4
            return distances, ids

    monkeypatch.setattr("routes.search.faiss_index", DummyFaissIndex())

    # DB post response
    mock_post = {
        "post_id": "1",
        "user_id": "1234",
        "cat_name": "Whiskers",
        "gender": "male",
        "color": "black",
        "breed": "Mixed",
        "location": {"latitude": 13.75, "longitude": 100.50},
        "lost_date": "2024-01-01T00:00:00",
        "email_notification": True,
        "post_type": "lost",
        "cat_image": {
            "image_id": "4",
            "stored_filename": "cat.jpg",
            "image_path": "uploads/cat.jpg",
            "faiss_ids": [401]
        },
        "status": "active",
        "user_email": "test@example.com"
    }

    class AsyncCursor:
        def __aiter__(self):
            async def iterator():
                yield mock_post
            return iterator()

    class MockCollection:
        def find(self, query):
            return AsyncCursor()

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "posts_v2":
                return MockCollection()
            raise KeyError()

    db_module.db.database = FakeDatabase()

    # Send request
    files = {"file": ("test.jpg", buf.getvalue(), "image/jpeg")}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/search/search", files=files)

    # print("Response:", response.status_code, response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "IMAGE_ONLY"
    assert data["count"] == 1
    assert data["results"][0]["post_id"] == "1"
    assert "similarity_percent" in data["results"][0]
