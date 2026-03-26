"""Tests for report generation and export endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_summary_report_empty(client: AsyncClient):
    resp = await client.get("/api/reports/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_images"] == 0


@pytest.mark.asyncio
async def test_summary_report_with_data(client: AsyncClient, sample_data):
    resp = await client.get("/api/reports/summary")
    data = resp.json()
    assert data["total_images"] == 5
    assert data["total_detections"] == 3
    assert data["total_species"] >= 1
    assert data["quoll_detections"] >= 1
    assert len(data["species_distribution"]) >= 1
    assert len(data["camera_counts"]) >= 1


@pytest.mark.asyncio
async def test_summary_report_species_filter(client: AsyncClient, sample_data):
    resp = await client.get("/api/reports/summary", params={"species": "quoll"})
    data = resp.json()
    assert data["total_detections"] >= 1


@pytest.mark.asyncio
async def test_export_csv(client: AsyncClient, sample_data):
    resp = await client.get("/api/reports/export", params={"format": "csv"})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "total_images" in resp.text


@pytest.mark.asyncio
async def test_export_json(client: AsyncClient, sample_data):
    resp = await client.get("/api/reports/export", params={"format": "json"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_images" in data
