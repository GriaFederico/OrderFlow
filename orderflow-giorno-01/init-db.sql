-- init-db.sql - OrderFlow Database Initialization
-- Executed automatically on first PostgreSQL startup
-- Mounted as read-only bind mount in docker-compose.yml

-- Create databases for each microservice
-- (orderflow_orders is created by POSTGRES_DB env var)
CREATE DATABASE orderflow_inventory;
CREATE DATABASE orderflow_notifications;

-- ============================================
-- Schema for orderflow_orders
-- ============================================
\c orderflow_orders;

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer ON orders(customer_name);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ============================================
-- Schema for orderflow_inventory
-- ============================================
\c orderflow_inventory;

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE NOT NULL,
    quantity_available INTEGER NOT NULL DEFAULT 0,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_sku ON products(sku);

-- Seed data: sample products
INSERT INTO products (name, sku, quantity_available, price) VALUES
    ('Laptop Pro 15', 'LAP-PRO-15', 50, 1299.99),
    ('Wireless Mouse', 'MOU-WIR-01', 200, 29.99),
    ('USB-C Hub', 'HUB-USC-01', 150, 49.99),
    ('Mechanical Keyboard', 'KEY-MEC-01', 75, 89.99),
    ('Monitor 27 4K', 'MON-27K-01', 30, 449.99);

-- ============================================
-- Schema for orderflow_notifications
-- ============================================
\c orderflow_notifications;

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX idx_notifications_order_id ON notifications(order_id);
CREATE INDEX idx_notifications_status ON notifications(status);
