#!/bin/bash

# Setup PostgreSQL for e-commerce application
echo "Setting up PostgreSQL database..."

# Create database and user as postgres user
sudo -u postgres psql << EOF
-- Create database
CREATE DATABASE ecommerce;

-- Create user with password
CREATE USER ecommerce_user WITH PASSWORD 'commercePASS';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ecommerce TO ecommerce_user;

-- Connect to ecommerce database and grant schema privileges
\c ecommerce
GRANT ALL ON SCHEMA public TO ecommerce_user;

-- List databases to confirm
\l

-- List users to confirm
\du
EOF

echo ""
echo "PostgreSQL setup complete!"
echo ""
echo "Testing connection..."
PGPASSWORD=commercePASS psql -U ecommerce_user -d ecommerce -h localhost -c "SELECT current_database(), current_user;"
