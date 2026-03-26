"""Tests for image listing, detail, and upload endpoints."""
import io
import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


@pytest.mark.asyncio
async def test_list_images_empty(client: AsyncClient):
    resp = await client.get("/api/images/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_images_with_data(client: AsyncClient, sample_data):
    resp = await client.get("/api/images/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_list_images_filter_processed(client: AsyncClient, sample_data):
    resp = await client.get("/api/images/", params={"processed": True})
    data = resp.json()
    assert data["total"] == 5  # all are processed in sample_data


@pytest.mark.asyncio
async def test_list_images_filter_has_animal(client: AsyncClient, sample_data):
    resp = await client.get("/api/images/", params={"has_animal": True})
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_list_images_pagination(client: AsyncClient, sample_data):
    resp = await client.get("/api/images/", params={"per_page": 2, "page": 1})
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_get_image_detail(client: AsyncClient, sample_data):
    img_id = sample_data["images"][0].id
    resp = await client.get(f"/api/images/{img_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "RCNX0000.JPG"
    assert data["camera"] is not None
    assert data["camera"]["name"] == "1A"


@pytest.mark.asyncio
async def test_get_image_not_found(client: AsyncClient):
    resp = await client.get("/api/images/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_images_by_species(client: AsyncClient, sample_data):
    resp = await client.get("/api/images/by-species/quoll")
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    resp = await client.post("/api/images/upload", files={"file": ("test.jpg", b"fake", "image/jpeg")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_single(client: AsyncClient, test_user):
    fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    resp = await client.post(
        "/api/images/upload",
        files={"file": ("test_img.jpg", fake_jpg, "image/jpeg")},
        headers=auth_header(test_user),
    )
    assert resp.status_code == 200
    assert resp.json()["filename"] == "test_img.jpg"


@pytest.mark.asyncio
async def test_upload_single_duplicate_filename_gets_suffix(client: AsyncClient, test_user):
    fake_jpg_a = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    fake_jpg_b = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x01" * 100)

    resp1 = await client.post(
        "/api/images/upload",
        files={"file": ("same_name.jpg", fake_jpg_a, "image/jpeg")},
        headers=auth_header(test_user),
    )
    resp2 = await client.post(
        "/api/images/upload",
        files={"file": ("same_name.jpg", fake_jpg_b, "image/jpeg")},
        headers=auth_header(test_user),
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["file_path"] != resp2.json()["file_path"]
    assert resp2.json()["filename"].startswith("same_name_")


@pytest.mark.asyncio
async def test_upload_bad_format(client: AsyncClient, test_user):
    resp = await client.post(
        "/api/images/upload",
        files={"file": ("test.txt", b"not an image", "text/plain")},
        headers=auth_header(test_user),
    )
    assert resp.status_code == 400
