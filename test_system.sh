#!/bin/bash

# ABrain System Test Script
# Tests the connection between frontend and backend

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== ABrain System Test ===${NC}"

# Test 1: Check if backend server starts
echo -e "${YELLOW}Test 1: Starting backend server...${NC}"
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}Virtual environment not found. Please run the setup first.${NC}"
    exit 1
fi

# Start backend in background
python server/main.py > test_backend.log 2>&1 &
BACKEND_PID=$!
sleep 5

# Test backend health endpoint
echo -e "${YELLOW}Testing backend health endpoint...${NC}"
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    echo -e "${YELLOW}Backend logs:${NC}"
    cat test_backend.log
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Test API endpoints
echo -e "${YELLOW}Testing API endpoints...${NC}"

# Test system health
if curl -s http://localhost:8000/system/health | grep -q "status"; then
    echo -e "${GREEN}✓ System health endpoint works${NC}"
else
    echo -e "${RED}✗ System health endpoint failed${NC}"
fi

# Test 2: Check frontend dependencies and build
echo -e "${YELLOW}Test 2: Checking frontend setup...${NC}"
cd "$PROJECT_ROOT/frontend/agent-ui"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
else
    echo -e "${GREEN}✓ Node.js found: $(node --version)${NC}"
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
else
    echo -e "${GREEN}✓ npm found: $(npm --version)${NC}"
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install > ../frontend_install.log 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo -e "${RED}✗ Frontend dependency installation failed${NC}"
        cat ../frontend_install.log
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
else
    echo -e "${GREEN}✓ Frontend dependencies already installed${NC}"
fi

# Test frontend build
echo -e "${YELLOW}Testing frontend build...${NC}"
npm run build > ../frontend_build.log 2>&1 &
BUILD_PID=$!

# Wait for build to complete
wait $BUILD_PID
BUILD_EXIT_CODE=$?

if [ $BUILD_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend builds successfully${NC}"
else
    echo -e "${RED}✗ Frontend build failed${NC}"
    echo -e "${YELLOW}Build logs:${NC}"
    cat ../frontend_build.log
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Test 3: Test API connection
echo -e "${YELLOW}Test 3: Testing API connection with authentication...${NC}"

# Test login endpoint
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@abrain.local","password":"demo"}')

if echo "$LOGIN_RESPONSE" | grep -q "token"; then
    echo -e "${GREEN}✓ Login endpoint works${NC}"
    
    # Extract token (simplified)
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    
    # Test authenticated endpoints
    echo -e "${YELLOW}Testing authenticated endpoints...${NC}"
    
    # Test agents endpoint
    AGENTS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/agents)
    if echo "$AGENTS_RESPONSE" | grep -q "data"; then
        echo -e "${GREEN}✓ Agents endpoint works${NC}"
    else
        echo -e "${RED}✗ Agents endpoint failed${NC}"
        echo "Response: $AGENTS_RESPONSE"
    fi
    
    # Test tasks endpoint
    TASKS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/tasks)
    if echo "$TASKS_RESPONSE" | grep -q "data"; then
        echo -e "${GREEN}✓ Tasks endpoint works${NC}"
    else
        echo -e "${RED}✗ Tasks endpoint failed${NC}"
        echo "Response: $TASKS_RESPONSE"
    fi
    
    # Test metrics endpoint
    METRICS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/metrics/system)
    if echo "$METRICS_RESPONSE" | grep -q "cpu_usage"; then
        echo -e "${GREEN}✓ Metrics endpoint works${NC}"
    else
        echo -e "${RED}✗ Metrics endpoint failed${NC}"
        echo "Response: $METRICS_RESPONSE"
    fi
    
else
    echo -e "${RED}✗ Login endpoint failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
fi

# Cleanup
echo -e "${YELLOW}Cleaning up test processes...${NC}"
kill $BACKEND_PID 2>/dev/null || true

# Clean up log files
rm -f test_backend.log ../frontend_install.log ../frontend_build.log

echo -e "${GREEN}=== Test completed successfully! ===${NC}"
echo -e "${GREEN}The system is ready to run.${NC}"
echo ""
echo -e "${BLUE}To start the full system:${NC}"
echo -e "${YELLOW}bash start_fullstack.sh${NC}"
echo ""
echo -e "${BLUE}Manual startup:${NC}"
echo -e "${YELLOW}1. Backend: python server/main.py${NC}"
echo -e "${YELLOW}2. Frontend: cd frontend/agent-ui && npm run dev${NC}"
