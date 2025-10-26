#!/bin/bash

# Setup script for NL to SQL Dashboard

echo "Setting up NL to SQL Dashboard..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Create database directory
mkdir -p database

# Start services
docker-compose -f docker/docker-compose.yml up -d

echo "Setup complete! Access the application at http://localhost:3000"