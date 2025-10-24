"""Webhook management endpoint"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import httpx
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: HttpUrl
    events: list[str] = ["document.ingested", "extraction.completed", "audit.completed"]
    secret: Optional[str] = None


class WebhookEvent(BaseModel):
    """Webhook event payload"""
    event_type: str
    timestamp: datetime
    document_id: str
    data: Dict[str, Any]


# In-memory webhook registry (in production, use database)
webhook_registry: Dict[str, WebhookConfig] = {}


@router.post("/webhook/register", status_code=status.HTTP_201_CREATED)
async def register_webhook(config: WebhookConfig):
    """
    Register a webhook URL to receive event notifications

    - **url**: The URL to POST events to
    - **events**: List of event types to subscribe to
    - **secret**: Optional secret for webhook signature verification
    """
    webhook_id = str(hash(config.url))
    webhook_registry[webhook_id] = config

    logger.info(f"Registered webhook: {config.url} for events: {config.events}")

    return {
        "webhook_id": webhook_id,
        "url": str(config.url),
        "events": config.events,
        "message": "Webhook registered successfully"
    }


@router.delete("/webhook/{webhook_id}")
async def unregister_webhook(webhook_id: str):
    """Unregister a webhook"""
    if webhook_id not in webhook_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    deleted = webhook_registry.pop(webhook_id)
    logger.info(f"Unregistered webhook: {deleted.url}")

    return {"message": "Webhook unregistered successfully"}


@router.get("/webhook/list")
async def list_webhooks():
    """List all registered webhooks"""
    return {
        "webhooks": [
            {
                "webhook_id": wid,
                "url": str(config.url),
                "events": config.events
            }
            for wid, config in webhook_registry.items()
        ],
        "total": len(webhook_registry)
    }


async def send_webhook_event(
    event_type: str,
    document_id: str,
    data: Dict[str, Any]
):
    """
    Send webhook event to all registered webhooks
    This function is called by other services when events occur
    """
    event = WebhookEvent(
        event_type=event_type,
        timestamp=datetime.utcnow(),
        document_id=document_id,
        data=data
    )

    # Find webhooks subscribed to this event type
    matching_webhooks = [
        config for config in webhook_registry.values()
        if event_type in config.events
    ]

    if not matching_webhooks:
        logger.debug(f"No webhooks registered for event: {event_type}")
        return

    # Send to all matching webhooks
    async with httpx.AsyncClient(timeout=10.0) as client:
        for config in matching_webhooks:
            try:
                headers = {"Content-Type": "application/json"}
                if config.secret:
                    headers["X-Webhook-Secret"] = config.secret

                response = await client.post(
                    str(config.url),
                    json=event.model_dump(mode='json'),
                    headers=headers
                )

                if response.status_code == 200:
                    logger.info(f"Webhook sent successfully to {config.url}")
                else:
                    logger.warning(
                        f"Webhook failed: {config.url} returned {response.status_code}"
                    )

            except Exception as e:
                logger.error(f"Failed to send webhook to {config.url}: {str(e)}")


@router.post("/webhook/test")
async def test_webhook(url: HttpUrl):
    """
    Test a webhook URL by sending a test event
    Useful for validating webhook endpoints before registration
    """
    test_event = WebhookEvent(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        document_id="test-document-id",
        data={"message": "This is a test webhook event"}
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                str(url),
                json=test_event.model_dump(mode='json'),
                headers={"Content-Type": "application/json"}
            )

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text[:200]  # First 200 chars
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook test failed: {str(e)}"
        )
