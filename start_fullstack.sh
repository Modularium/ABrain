#!/bin/bash

# ABrain Full Stack Startup Script
# Starts both backend and frontend services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The script lives in the project root, so use that directly
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}=== ABrain Full Stack Startup ===${NC}"
echo -e "${BLUE}Project root: ${PROJECT_ROOT}${NC}"

# Function to check if a port is in use
check_port() {
    local port="$1"
    python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(1)
    s.connect(("127.0.0.1", port))
except Exception:
    sys.exit(1)
sys.exit(0)
PY
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing processes on port $port...${NC}"
    
    # Find and kill processes using the port
    if command -v lsof &> /dev/null; then
        lsof -ti:$port 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    elif command -v fuser &> /dev/null; then
        fuser -k "${port}/tcp" 2>/dev/null || true
    else
        echo -e "${RED}Unable to automatically free port $port. Please close the process manually.${NC}"
    fi
}

# Check and kill processes on required ports
echo -e "${YELLOW}Checking for existing services...${NC}"

if check_port 8000; then
    echo -e "${YELLOW}Port 8000 is in use, stopping existing backend...${NC}"
    kill_port 8000
    sleep 2
fi

if check_port 3000; then
    echo -e "${YELLOW}Port 3000 is in use, stopping existing frontend...${NC}"
    kill_port 3000
    sleep 2
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${RED}Virtual environment not found at $PROJECT_ROOT/.venv${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    cd "$PROJECT_ROOT"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${YELLOW}Installing requirements...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}Virtual environment created and dependencies installed${NC}"
else
    echo -e "${GREEN}Virtual environment found${NC}"
fi

# Start Backend Server
echo -e "${BLUE}Starting Backend Server on port 8000...${NC}"
cd "$PROJECT_ROOT"
source .venv/bin/activate

# Start the backend in the background
python server/main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID" > backend.pid

# Wait for backend to start
echo -e "${YELLOW}Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running on http://localhost:8000${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend failed to start within 30 seconds${NC}"
        echo -e "${YELLOW}Backend logs:${NC}"
        tail -20 backend.log
        exit 1
    fi
    sleep 1
done

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js 18+ and try again.${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm is not installed. Please install npm and try again.${NC}"
    exit 1
fi

# Start Frontend
echo -e "${BLUE}Starting Frontend...${NC}"
cd "$PROJECT_ROOT/frontend/agent-ui"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Start the frontend development server in the background
echo -e "${BLUE}Starting frontend development server on port 3000...${NC}"
npm run dev > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID" > ../../frontend.pid

# Wait for frontend to start
echo -e "${YELLOW}Waiting for frontend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is running on http://localhost:3000${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Frontend failed to start within 30 seconds${NC}"
        echo -e "${YELLOW}Frontend logs:${NC}"
        tail -20 ../../frontend.log
        
        # Kill backend if frontend failed
        if [ ! -z "$BACKEND_PID" ]; then
            kill $BACKEND_PID 2>/dev/null || true
        fi
        exit 1
    fi
    sleep 1
done

echo -e "${GREEN}=== ABrain is now running! ===${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}Backend API: http://localhost:8000${NC}"
echo -e "${GREEN}API Documentation: http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo -e "${BLUE}Service logs:${NC}"
echo -e "${YELLOW}Backend logs: tail -f backend.log${NC}"
echo -e "${YELLOW}Frontend logs: tail -f frontend.log${NC}"

# Function to handle cleanup
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${YELLOW}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill backend
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${YELLOW}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Clean up port processes
    kill_port 3000
    kill_port 8000
    
    # Remove PID files
    rm -f backend.pid frontend.pid
    
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user to stop
while true; do
    sleep 1
done
