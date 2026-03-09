# OrderFlow - Order Service
# FastAPI application for managing orders
# Run locally: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Run in Docker: docker run -p 8000:8000 corso-devops/order-service:latest

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("order-service")

app = FastAPI(
    title="OrderFlow - Order Service",
    description="Gestione ordini per la piattaforma OrderFlow",
    version="1.0.0"
)

# In-memory storage (will be replaced by PostgreSQL in Docker Compose lesson)
orders_db: dict = {}
order_counter = 0


class OrderCreate(BaseModel):
    """Schema for creating a new order."""
    customer_name: str
    product_id: int
    quantity: int
    notes: Optional[str] = None


class Order(BaseModel):
    """Schema for order response."""
    id: int
    customer_name: str
    product_id: int
    quantity: int
    status: str
    notes: Optional[str]
    created_at: str


@app.get("/health")
def health_check():
    """Health check endpoint for Docker HEALTHCHECK and load balancers."""
    return {
        "status": "healthy",
        "service": "order-service",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/api/orders")
def list_orders():
    """List all orders."""
    return {"orders": list(orders_db.values()), "total": len(orders_db)}


@app.post("/api/orders", status_code=201)
def create_order(order: OrderCreate):
    """Create a new order."""
    global order_counter
    order_counter += 1

    new_order = {
        "id": order_counter,
        "customer_name": order.customer_name,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "status": "pending",
        "notes": order.notes,
        "created_at": datetime.utcnow().isoformat()
    }
    orders_db[order_counter] = new_order

    logger.info(f"Order created: id={order_counter}, customer={order.customer_name}")
    return new_order


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    """Get a specific order by ID."""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return orders_db[order_id]


@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: int, status: str):
    """Update the status of an order."""
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid statuses: {valid_statuses}"
        )

    orders_db[order_id]["status"] = status
    logger.info(f"Order {order_id} status updated to {status}")
    return orders_db[order_id]
