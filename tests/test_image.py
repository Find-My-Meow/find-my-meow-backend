
from PIL import Image as PILImage
import io
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock
from routes.image import image_router
from core import database as db_module

app = FastAPI()
app.include_router(image_router, prefix="/api/v1/image")


@pytest.mark.asyncio
async def test_upload_image(monkeypatch, tmp_path):
    # Create a dummy image in memory
    dummy_image = PILImage.new("RGB", (100, 100), color="gray")
    buf = io.BytesIO()
    dummy_image.save(buf, format="JPEG")
    buf.seek(0)

    # Mock all image processing and storage steps
    # detect cat
    monkeypatch.setattr("routes.image.detect_cats",
                        lambda img: [[0, 0, 100, 100]])
    # crop cat
    monkeypatch.setattr("routes.image.crop_cats", lambda img, det: [img])
    # extract feature
    monkeypatch.setattr("routes.image.extract_cat_features", lambda crops: [
                        [[0.1]*512]])  # fake feature vector
    # get image id
    monkeypatch.setattr("routes.image.get_next_image_id",
                        AsyncMock(return_value="4"))
    # sanitize image
    monkeypatch.setattr("routes.image.sanitize_image", lambda f: buf)
    # upload to s3
    monkeypatch.setattr("routes.image.upload_to_s3", lambda f, ext: (
        "https://mocked-s3-url.com/image.jpg", "mocked_image.jpg"))
    # add to faiss
    monkeypatch.setattr(
        "routes.image.faiss_index.add_with_ids", lambda vectors, ids: None)
    monkeypatch.setattr("routes.image.faiss.write_index",
                        lambda index, file: None)
    monkeypatch.setattr("routes.image.upload_faiss_index_to_s3", lambda: None)

    # Mock database insert
    mock_collection = AsyncMock()
    mock_collection.insert_one.return_value = None

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "images_v2":
                return mock_collection
            raise KeyError()

    db_module.db.database = FakeDatabase()

    files = {"file": ("dummy.jpg", buf.getvalue(), "image/jpeg")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/image/", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["image_id"] == "4"
    assert data["stored_filename"] == "mocked_image.jpg"
    assert data["image_path"].startswith("https://mocked-s3-url")
    assert isinstance(data["faiss_ids"], list)


@pytest.mark.asyncio
async def test_get_image_by_id(monkeypatch):
    mock_image_data = {
        "image_id": "1",
        "stored_filename": "findmymeow_cat.jpg",
        "image_path": "https://findmymeow.com/findmymeow_cat.jpg",
        "faiss_ids": [100, 101, 102]
    }

    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = mock_image_data

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "images_v2":
                return mock_collection
            raise KeyError()

    db_module.db.database = FakeDatabase()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/image/1")

    print("Response:", response.status_code, response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["image_id"] == "1"
    assert data["stored_filename"] == "findmymeow_cat.jpg"


@pytest.mark.asyncio
async def test_delete_image_by_id(monkeypatch):
    mock_image_data = {
        "image_id": "1",
        "stored_filename": "findmymeow_cat.jpg",
        "image_path": "https://findmymeow.com/findmymeow_cat.jpg",
        "faiss_ids": [100, 101, 102]
    }

    mock_collection = AsyncMock()
    mock_collection.find_one.return_value = mock_image_data
    mock_collection.delete_one.return_value = None

    # delete from s3
    monkeypatch.setattr(
        "routes.image.s3_client.delete_object", lambda **kwargs: None)
    # delete faiss index
    monkeypatch.setattr("routes.image.get_all_faiss_ids",
                        lambda index: [101, 102, 103, 200])
    monkeypatch.setattr(
        "routes.image.faiss_index.remove_ids", lambda ids: None)
    monkeypatch.setattr("routes.image.faiss.write_index",
                        lambda index, file: None)
    # update faiss
    monkeypatch.setattr("routes.image.upload_faiss_index_to_s3", lambda: None)

    class FakeDatabase:
        def __getitem__(self, name):
            if name == "images_v2":
                return mock_collection
            raise KeyError()

    db_module.db.database = FakeDatabase()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete("/api/v1/image/1")

    assert response.status_code == 200
    assert response.json()["message"] == "Image deleted successfully"


@pytest.mark.asyncio
async def test_check_image_quality(monkeypatch, tmp_path):
    # Create a small dummy image
    from PIL import Image as PILImage
    dummy_image_path = tmp_path / "test.jpg"
    PILImage.new("RGB", (20, 20), color="gray").save(dummy_image_path)

    def mock_is_blurry(image, threshold):
        return True

    def mock_is_too_small(image):
        return True

    monkeypatch.setattr("routes.image.is_blurry", mock_is_blurry)
    monkeypatch.setattr("routes.image.is_too_small", mock_is_too_small)

    with dummy_image_path.open("rb") as f:
        files = {"file": ("test.jpg", f, "image/jpeg")}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/v1/image/check-quality", files=files)

    assert response.status_code == 200
    assert "resolution" in response.json()["issues"]
    assert "blurry" in response.json()["issues"]
