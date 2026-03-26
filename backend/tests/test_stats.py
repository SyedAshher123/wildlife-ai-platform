"""Tests for dashboard statistics endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_stats_empty(client: AsyncClient):
    resp = await client.get("/api/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_images"] == 0
    assert data["processing_percent"] == 0.0


@pytest.mark.asyncio
async def test_dashboard_stats_with_data(client: AsyncClient, sample_data):
    resp = await client.get("/api/stats/")
    data = resp.json()
    assert data["total_images"] == 5
    assert data["processed_images"] == 5
    assert data["total_detections"] == 3
    assert data["quoll_detections"] >= 1
    assert data["total_cameras"] >= 1


@pytest.mark.asyncio
async def test_camera_stats(client: AsyncClient, sample_data):
    resp = await client.get("/api/stats/cameras")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "1A"
    assert data[0]["image_count"] == 5
    assert data[0]["latitude"] is not None


@pytest.mark.asyncio
async def test_collection_stats(client: AsyncClient, sample_data):
    resp = await client.get("/api/stats/collections")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_individual_stats_empty(client: AsyncClient):
    resp = await client.get("/api/stats/individuals")
    assert resp.status_code == 200
    assert resp.json() == []
