"""Tests for annotation CRUD (create, read, update)."""
import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_annotation(client: AsyncClient, test_user, sample_data):
    det_id = sample_data["detections"][0].id
    resp = await client.post("/api/annotations/", json={
        "detection_id": det_id,
        "is_correct": True,
        "notes": "Looks like a quoll",
    }, headers=auth_header(test_user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["detection_id"] == det_id
    assert data["is_correct"] is True
    assert data["annotator"] == test_user.email


@pytest.mark.asyncio
async def test_create_annotation_missing_detection(client: AsyncClient, test_user):
    resp = await client.post("/api/annotations/", json={
        "detection_id": 9999, "is_correct": False,
    }, headers=auth_header(test_user))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_annotation_requires_auth(client: AsyncClient, sample_data):
    det_id = sample_data["detections"][0].id
    resp = await client.post("/api/annotations/", json={"detection_id": det_id, "is_correct": True})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_annotations_for_detection(client: AsyncClient, test_user, sample_data):
    det_id = sample_data["detections"][0].id
    await client.post("/api/annotations/", json={
        "detection_id": det_id, "is_correct": True,
    }, headers=auth_header(test_user))

    resp = await client.get(f"/api/annotations/by-detection/{det_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_annotation(client: AsyncClient, test_user, sample_data):
    det_id = sample_data["detections"][0].id
    create_resp = await client.post("/api/annotations/", json={
        "detection_id": det_id, "is_correct": True,
    }, headers=auth_header(test_user))
    ann_id = create_resp.json()["id"]

    resp = await client.put(f"/api/annotations/{ann_id}", json={
        "is_correct": False,
        "corrected_species": "Trichosurus sp | Brushtail Possum sp",
        "notes": "Actually a possum",
    }, headers=auth_header(test_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is False
    assert data["corrected_species"] == "Trichosurus sp | Brushtail Possum sp"


@pytest.mark.asyncio
async def test_annotation_individual_assignment(client: AsyncClient, test_user, sample_data):
    det_id = sample_data["detections"][0].id
    resp = await client.post("/api/annotations/", json={
        "detection_id": det_id,
        "is_correct": True,
        "individual_id": "02Q2",
    }, headers=auth_header(test_user))
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_annotation_flag_retraining(client: AsyncClient, test_user, sample_data):
    det_id = sample_data["detections"][1].id
    resp = await client.post("/api/annotations/", json={
        "detection_id": det_id,
        "is_correct": False,
        "corrected_species": "Felis catus | Domestic Cat",
        "flag_for_retraining": True,
    }, headers=auth_header(test_user))
    assert resp.status_code == 201
