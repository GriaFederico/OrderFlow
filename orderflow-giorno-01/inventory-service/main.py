# OrderFlow - Inventory Service with stock management
# Settimana 3, Giorno 4 — Architettura Microservizi
#
# Provides:
#   - Product catalog (CRUD)
#   - Stock availability check (used by order-service)
#   - Stock update endpoint
#   - Correlation ID propagation
#
# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [corr=%(correlation_id)s] %(message)s",
    defaults={"correlation_id": "none"}
)
logger = logging.getLogger("inventory-service")

app = FastAPI(title="OrderFlow - Inventory Service", version="2.0.0")

# In-memory product catalog (PostgreSQL in production)
products_db = {
    1: {"id": 1, "name": "Laptop Pro 15", "price": 1299.99, "stock": 50, "category": "electronics"},
    2: {"id": 2, "name": "Wireless Mouse", "price": 29.99, "stock": 200, "category": "accessories"},
    3: {"id": 3, "name": "USB-C Hub", "price": 49.99, "stock": 150, "category": "accessories"},
    4: {"id": 4, "name": "Monitor 27 4K", "price": 449.99, "stock": 30, "category": "electronics"},
    5: {"id": 5, "name": "Mechanical Keyboard", "price": 89.99, "stock": 100, "category": "accessories"},
}


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None


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
    return {"status": "healthy", "service": "inventory-service", "version": "2.0.0"}


@app.get("/api/products")
def list_products():
    """List all products in the catalog."""
    return {"products": list(products_db.values()), "total": len(products_db)}


@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    """Get a specific product by ID."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return products_db[product_id]


@app.get("/api/products/{product_id}/check-stock")
def check_stock(product_id: int, quantity: int = 1, request: Request = None):
    """
    Check if the requested quantity is available in stock.
    Used by order-service during order creation (synchronous call).
    """
    correlation_id = getattr(request.state, "correlation_id", "none") if request else "none"

    if product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product = products_db[product_id]
    available = product["stock"] >= quantity

    logger.info(
        f"Stock check: product={product_id}, requested={quantity}, "
        f"stock={product['stock']}, available={available}",
        extra={"correlation_id": correlation_id}
    )

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "requested": quantity,
        "current_stock": product["stock"],
        "available": available
    }


@app.patch("/api/products/{product_id}/stock")
def update_stock(product_id: int, quantity_change: int, request: Request = None):
    """
    Update stock level. Use negative values to decrease stock.
    Example: quantity_change=-5 reduces stock by 5.
    """
    correlation_id = getattr(request.state, "correlation_id", "none") if request else "none"

    if product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product = products_db[product_id]
    new_stock = product["stock"] + quantity_change

    if new_stock < 0:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient stock. Current: {product['stock']}, requested change: {quantity_change}"
        )

    product["stock"] = new_stock

    logger.info(
        f"Stock updated: product={product_id}, change={quantity_change}, new_stock={new_stock}",
        extra={"correlation_id": correlation_id}
    )

    return {
        "product_id": product_id,
        "previous_stock": product["stock"] - quantity_change,
        "new_stock": new_stock
    }
