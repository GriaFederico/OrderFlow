# OrderFlow - Notification Service
# Settimana 3, Giorno 4 — Architettura Microservizi
#
# Receives order events from other services and maintains a notification log.
# In production, this would send emails via SES or SMS via SNS (Settimana 2, Giorno 3).
# In the Docker Compose environment, it logs notifications internally.
#
# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [corr=%(correlation_id)s] %(message)s",
    defaults={"correlation_id": "none"}
)
logger = logging.getLogger("notification-service")

app = FastAPI(title="OrderFlow - Notification Service", version="2.0.0")

# In-memory notification log
notifications_db: list = []
notification_counter = 0


class NotificationCreate(BaseModel):
    order_id: int
    customer_name: str
    event_type: str
    timestamp: Optional[str] = None


# --- Middleware ---

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Propagate X-Correlation-ID from incoming requests."""
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# --- Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "notification-service", "version": "2.0.0"}


@app.post("/api/notifications", status_code=201)
def create_notification(notification: NotificationCreate, request: Request = None):
    """
    Receive an order event and log the notification.
    Called by order-service in fire-and-forget mode.
    """
    global notification_counter
    correlation_id = getattr(request.state, "correlation_id", "none") if request else "none"

    notification_counter += 1

    # Map event type to human-readable notification message
    messages = {
        "order.created": f"Ordine #{notification.order_id} creato per {notification.customer_name}",
        "order.confirmed": f"Ordine #{notification.order_id} confermato",
        "order.shipped": f"Ordine #{notification.order_id} spedito",
        "order.delivered": f"Ordine #{notification.order_id} consegnato",
        "order.cancelled": f"Ordine #{notification.order_id} annullato",
    }

    new_notification = {
        "id": notification_counter,
        "order_id": notification.order_id,
        "customer_name": notification.customer_name,
        "event_type": notification.event_type,
        "message": messages.get(notification.event_type, f"Event: {notification.event_type}"),
        "channel": "log",  # In production: "email", "sms", "push"
        "status": "sent",
        "created_at": datetime.utcnow().isoformat()
    }
    notifications_db.append(new_notification)

    logger.info(
        f"Notification created: order={notification.order_id}, "
        f"event={notification.event_type}, channel=log",
        extra={"correlation_id": correlation_id}
    )

    return new_notification


@app.get("/api/notifications")
def list_notifications(order_id: Optional[int] = None):
    """List notifications, optionally filtered by order_id."""
    if order_id:
        filtered = [n for n in notifications_db if n["order_id"] == order_id]
        return {"notifications": filtered, "total": len(filtered)}
    return {"notifications": notifications_db, "total": len(notifications_db)}


@app.get("/api/notifications/{notification_id}")
def get_notification(notification_id: int):
    """Get a specific notification by ID."""
    for n in notifications_db:
        if n["id"] == notification_id:
            return n
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")
