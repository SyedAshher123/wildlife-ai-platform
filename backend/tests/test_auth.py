"""Tests for authentication endpoints: register, login, token validation, roles."""
import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "new@example.com", "password": "securepass1", "full_name": "New User", "role": "researcher",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "researcher"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password123"})
    resp = await client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_role(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"email": "bad@example.com", "password": "password123", "role": "superuser"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "login@example.com", "password": "password123"})
    resp = await client.post("/api/auth/login", data={"username": "login@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "wrong@example.com", "password": "password123"})
    resp = await client.post("/api/auth/login", data={"username": "wrong@example.com", "password": "badpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, test_user):
    resp = await client.get("/api/auth/me", headers=auth_header(test_user))
    assert resp.status_code == 200
    assert resp.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401
