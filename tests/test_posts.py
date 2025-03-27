import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock
from models.post import Post
from routes.posts import post_router
from core import database as db_module

app = FastAPI()
app.include_router(post_router, prefix="/api/v1/posts")


@pytest.fixture
def dummy_image(tmp_path):
    file = tmp_path / "dummy.jpg"
    file.write_bytes(b"test image content")
    return file


@pytest.fixture
def mock_post_data():
    return {
        "user_id": "1234",
        "cat_name": "Milo",
        "gender": "male",
        "color": "black",
        "breed": "Siamese",
        "cat_marking": "white paws",
        "location": '{"latitude": 13.7563, "longitude": 100.5018}',
        "lost_date": "2024-02-22",
        "other_information": "Very shy",
        "email_notification": "true",
        "post_type": "lost",
        "user_email": "user@example.com",
    }


@pytest.mark.asyncio
async def test_create_post(monkeypatch, dummy_image, mock_post_data):
    mock_uploaded_image = {
        "image_id": "1",
        "stored_filename": "cat.jpg",
        "image_path": "uploads/cat.jpg",
        "faiss_ids": [100, 101, 102],
    }

    # upload image
    monkeypatch.setattr("routes.posts.upload_cat_image",
                        AsyncMock(return_value=mock_uploaded_image))
    # get post id
    monkeypatch.setattr("routes.posts.get_next_post_id",
                        AsyncMock(return_value="1"))
    monkeypatch.setattr("routes.posts.refresh_faiss_index", lambda: None)

    mock_collection = AsyncMock()
    mock_collection.insert_one.return_value.inserted_id = "mocked_id"

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "posts_v2":
                return mock_collection
            raise KeyError(f"Unknown collection: {name}")

    db_module.db.database = FakeDatabase()

    files = {"cat_image": (
        "dummy.jpg", dummy_image.read_bytes(), "image/jpeg")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/posts/", data=mock_post_data, files=files)

    assert response.status_code == 200
    post = Post(**response.json())
    assert post.post_id == "1"
    assert post.cat_name == "Milo"
    assert post.cat_image.image_id == "1"


@pytest.mark.asyncio
async def test_get_all_posts(monkeypatch):
    mock_posts = [
        {
            "post_id": "1",
            "user_id": "1234",
            "cat_name": "Milo",
            "gender": "male",
            "color": "black",
            "breed": "Siamese",
            "cat_marking": "white paws",
            "location": {"latitude": 13.7563, "longitude": 100.5018},
            "lost_date": "2024-02-22T00:00:00",
            "other_information": "Very shy",
            "email_notification": True,
            "post_type": "lost",
            "cat_image": {
                "image_id": "1",
                "stored_filename": "cat.jpg",
                "image_path": "uploads/cat.jpg",
                "faiss_ids": [100]
            },
            "status": "active",
            "user_email": "user@example.com"
        }
    ]

    # Dummy object returned by `find()` that supports `.to_list()`
    class DummyFindResult:
        async def to_list(self, length):
            return mock_posts

    def mock_find(query):
        return DummyFindResult()

    # Mock collection
    mock_collection = AsyncMock()
    mock_collection.find = mock_find 

    # Fake DB that returns the mock collection
    class FakeDatabase:
        def __getitem__(self, name):
            return mock_collection

    db_module.db.database = FakeDatabase()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/posts/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["post_id"] == "1"


@pytest.mark.asyncio
async def test_get_post_by_id(monkeypatch):
    mock_post = {
        "post_id": "1",
        "user_id": "1234",
        "cat_name": "Milo",
        "gender": "male",
        "color": "black",
        "breed": "Siamese",
        "cat_marking": "white paws",
        "location": {"latitude": 13.7563, "longitude": 100.5018},
        "lost_date": "2024-02-22T00:00:00",
        "other_information": "Very shy",
        "email_notification": True,
        "post_type": "lost",
        "cat_image": {
            "image_id": "1",
            "stored_filename": "cat.jpg",
            "image_path": "uploads/cat.jpg",
            "faiss_ids": [100, 101, 102]
        },
        "status": "active",
        "user_email": "user@example.com"
    }

    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = mock_post

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "posts_v2":
                return mock_collection
            raise KeyError()

    db_module.db.database = FakeDatabase()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/posts/1")

    assert response.status_code == 200
    assert response.json()["post_id"] == "1"
    assert response.json()["cat_name"] == "Milo"


@pytest.mark.asyncio
async def test_get_posts_by_user_id(monkeypatch):
    mock_posts = [{
        "post_id": "1",
        "user_id": "1234",
        "cat_name": "Milo",
        "gender": "male",
        "color": "black",
        "breed": "Siamese",
        "cat_marking": "white paws",
        "location": {"latitude": 13.7563, "longitude": 100.5018},
        "lost_date": "2024-02-22T00:00:00",
        "other_information": "Very shy",
        "email_notification": True,
        "post_type": "lost",
        "cat_image": {
            "image_id": "1",
            "stored_filename": "cat.jpg",
            "image_path": "uploads/cat.jpg",
            "faiss_ids": [100, 101, 102]
        },
        "status": "active",
        "user_email": "user@example.com"
    }]

    # Create dummy result
    class DummyFindResult:
        async def to_list(self, length=None):
            return mock_posts

    def mock_find(query):
        return DummyFindResult()

    # Inject into mocked collection
    mock_collection = AsyncMock()
    mock_collection.find = mock_find

    class FakeDatabase:
        def __getitem__(self, name):
            return mock_collection

    db_module.db.database = FakeDatabase()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/posts/user/1234")

    assert response.status_code == 200
    assert response.json()[0]["user_id"] == "1234"


@pytest.mark.asyncio
async def test_update_post(monkeypatch, dummy_image):
    # Existing post in the DB
    existing_post = {
        "post_id": "1",
        "user_id": "1234",
        "cat_name": "Milo",
        "gender": "male",
        "color": "black",
        "breed": "Siamese",
        "cat_marking": "white paws",
        "location": {"latitude": 13.7563, "longitude": 100.5018},
        "lost_date": "2024-02-22T00:00:00",
        "other_information": "Very shy",
        "email_notification": True,
        "post_type": "lost",
        "cat_image": {
            "image_id": "old_image_id",
            "stored_filename": "old.jpg",
            "image_path": "uploads/old.jpg",
            "faiss_ids": [101]
        },
        "status": "active",
        "user_email": "user@example.com"
    }

    # Simulate updated post (color and image changed)
    updated_post = {**existing_post, "color": "white"}
    updated_post["cat_image"] = {
        "image_id": "new_image_id",
        "stored_filename": "new.jpg",
        "image_path": "uploads/new.jpg",
        "faiss_ids": [999]
    }

    # Mocks
    mock_collection = AsyncMock()
    mock_collection.find_one.side_effect = [
        existing_post, updated_post]  # before and after update
    mock_collection.update_one.return_value = None

    monkeypatch.setattr("routes.posts.upload_cat_image",
                        AsyncMock(return_value=updated_post["cat_image"]))
    monkeypatch.setattr("routes.posts.delete_image_service", AsyncMock())
    monkeypatch.setattr("routes.posts.refresh_faiss_index", lambda: None)

    # Mock DB
    class FakeDatabase:
        def __getitem__(self, name):
            return mock_collection

    db_module.db.database = FakeDatabase()

    data = {
        "user_id": "1234",
        "color": "white"
    }

    files = {"cat_image": (
        "dummy.jpg", dummy_image.read_bytes(), "image/jpeg")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.put("/api/v1/posts/1", data=data, files=files)

    # Assertions
    assert response.status_code == 200
    body = response.json()
    assert body["color"] == "white"
    assert body["cat_image"]["image_id"] == "new_image_id"


@pytest.mark.asyncio
async def test_delete_post(monkeypatch):
    # Existing post in the DB
    post_data = {
        "post_id": "1",
        "cat_image": {
            "image_id": "image123",
            "stored_filename": "cat.jpg",
            "image_path": "uploads/cat.jpg",
            "faiss_ids": [123]
        }
    }

    # Mock collection
    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = post_data
    mock_collection.delete_one.return_value = None

    # delete image
    monkeypatch.setattr("routes.posts.delete_image_service", AsyncMock())
    monkeypatch.setattr("routes.posts.refresh_faiss_index", lambda: None)

    # Fake DB
    class FakeDatabase:
        def __getitem__(self, name):
            return mock_collection

    db_module.db.database = FakeDatabase()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete("/api/v1/posts/1")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Post deleted successfully"
    assert body["post_id"] == "1"
