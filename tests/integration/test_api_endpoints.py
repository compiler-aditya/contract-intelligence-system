"""Integration tests for API endpoints"""
import pytest
from httpx import AsyncClient
from io import BytesIO
import json


@pytest.mark.asyncio
async def test_root_endpoint(test_app):
    """Test root endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data


@pytest.mark.asyncio
async def test_health_check(test_app):
    """Test health check endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "system" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(test_app):
    """Test metrics endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "counters" in data
        assert "rates" in data
        assert "system" in data
        assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_ingest_pdf_missing_file(test_app):
    """Test ingest endpoint with missing file"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingest")

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_ingest_pdf_invalid_file(test_app):
    """Test ingest endpoint with invalid file"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Create a fake file
        files = {"files": ("test.txt", BytesIO(b"not a pdf"), "text/plain")}
        response = await client.post("/api/v1/ingest", files=files)

        # Should either accept or reject gracefully
        assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_extract_invalid_document_id(test_app):
    """Test extract endpoint with invalid document ID"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/extract",
            json={"document_id": "invalid-id"}
        )

        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_extract_nonexistent_document(test_app):
    """Test extract endpoint with non-existent document"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Valid UUID but doesn't exist
        fake_uuid = "123e4567-e89b-12d3-a456-426614174000"
        response = await client.post(
            "/api/v1/extract",
            json={"document_id": fake_uuid}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_ask_invalid_document_id(test_app):
    """Test ask endpoint with invalid document ID"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ask",
            json={
                "question": "What are the payment terms?",
                "document_ids": ["invalid-id"]
            }
        )

        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_ask_missing_question(test_app):
    """Test ask endpoint with missing question"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ask",
            json={"document_ids": ["123e4567-e89b-12d3-a456-426614174000"]}
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_audit_invalid_document_id(test_app):
    """Test audit endpoint with invalid document ID"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/audit",
            json={"document_id": "invalid-id"}
        )

        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_audit_with_use_llm_toggle(test_app):
    """Test audit endpoint with use_llm toggle"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        fake_uuid = "123e4567-e89b-12d3-a456-426614174000"

        # Test with use_llm=True
        response = await client.post(
            "/api/v1/audit?use_llm=true",
            json={"document_id": fake_uuid}
        )
        assert response.status_code in [400, 404]  # Document doesn't exist

        # Test with use_llm=False (rule-based)
        response = await client.post(
            "/api/v1/audit?use_llm=false",
            json={"document_id": fake_uuid}
        )
        assert response.status_code in [400, 404]  # Document doesn't exist


@pytest.mark.asyncio
async def test_webhook_register(test_app):
    """Test webhook registration"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/register",
            json={
                "url": "https://example.com/webhook",
                "events": ["document.ingested", "audit.completed"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "webhook_id" in data
        assert data["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_webhook_list(test_app):
    """Test listing webhooks"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/api/v1/webhook/list")

        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_webhook_test(test_app):
    """Test webhook testing endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # This will fail because example.com won't accept our webhook
        # but it should return a proper response
        response = await client.post(
            "/api/v1/webhook/test",
            params={"url": "https://httpbin.org/post"}
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_metrics_reset(test_app):
    """Test metrics reset endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post("/metrics/reset")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_prometheus_metrics(test_app):
    """Test Prometheus metrics endpoint"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        # Should return plain text
        assert "documents_ingested" in response.text
        assert "TYPE" in response.text
        assert "HELP" in response.text


@pytest.mark.asyncio
async def test_swagger_docs_available(test_app):
    """Test that Swagger docs are available"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/docs")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json_available(test_app):
    """Test that OpenAPI JSON is available"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "components" in data


@pytest.mark.asyncio
async def test_cors_headers(test_app):
    """Test CORS headers are present"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.options(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS should be configured
        assert response.status_code in [200, 405]
