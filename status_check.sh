#!/bin/bash

# ABrain Status Monitor
# Überwacht den Status von Frontend und Backend

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local endpoint=${3:-""}
    
    if curl -s http://localhost:$port$endpoint >/dev/null 2>&1; then
        echo -e "${GREEN}✓ $service_name is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}✗ $service_name is NOT running on port $port${NC}"
        return 1
    fi
}

# Function to test API endpoints
test_api() {
    echo -e "${BLUE}Testing API endpoints...${NC}"
    
    # Test health endpoint
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "${GREEN}✓ Health endpoint working${NC}"
    else
        echo -e "${RED}✗ Health endpoint failed${NC}"
        return 1
    fi
    
    # Test authentication
    local login_response=$(curl -s -X POST http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"demo@abrain.local","password":"demo"}')
    
    if echo "$login_response" | grep -q "token"; then
        echo -e "${GREEN}✓ Authentication working${NC}"
        
        # Extract token for further tests
        local token=$(echo "$login_response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
        
        # Test agents endpoint
        if curl -s -H "Authorization: Bearer $token" http://localhost:8000/agents | grep -q "data"; then
            echo -e "${GREEN}✓ Agents endpoint working${NC}"
        else
            echo -e "${RED}✗ Agents endpoint failed${NC}"
        fi
        
        # Test metrics endpoint
        if curl -s -H "Authorization: Bearer $token" http://localhost:8000/metrics/system | grep -q "cpu_usage"; then
            echo -e "${GREEN}✓ Metrics endpoint working${NC}"
        else
            echo -e "${RED}✗ Metrics endpoint failed${NC}"
        fi
        
    else
        echo -e "${RED}✗ Authentication failed${NC}"
        return 1
    fi
}

echo -e "${BLUE}=== ABrain Status Monitor ===${NC}"
echo -e "${BLUE}$(date)${NC}"
echo ""

# Check backend
echo -e "${YELLOW}Checking Backend...${NC}"
if check_service "Backend API" 8000 "/health"; then
    test_api
else
    echo -e "${RED}Backend is not responding${NC}"
fi

echo ""

# Check frontend
echo -e "${YELLOW}Checking Frontend...${NC}"
check_service "Frontend" 3001 || check_service "Frontend" 3000

echo ""

# Show service URLs
echo -e "${BLUE}Service URLs:${NC}"
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}Backend API: http://localhost:8000${NC}"
    echo -e "${GREEN}API Docs: http://localhost:8000/docs${NC}"
fi

if curl -s http://localhost:3001 >/dev/null 2>&1; then
    echo -e "${GREEN}Frontend: http://localhost:3001${NC}"
elif curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
fi

echo ""
echo -e "${BLUE}Login Credentials:${NC}"
echo -e "${YELLOW}Email: demo@abrain.local${NC}"
echo -e "${YELLOW}Password: demo${NC}"

echo ""
echo -e "${BLUE}Process Information:${NC}"
if [ -f "backend.pid" ]; then
    echo -e "${YELLOW}Backend PID: $(cat backend.pid)${NC}"
fi
if [ -f "frontend.pid" ]; then
    echo -e "${YELLOW}Frontend PID: $(cat frontend.pid)${NC}"
fi
