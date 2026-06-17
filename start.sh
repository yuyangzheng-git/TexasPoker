#!/bin/bash
# Poker LLM Agent Game 启动脚本

set -e

# 颜色
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "${CYAN}=====================================${NC}"
echo "${CYAN}   Poker LLM Agent Game Launcher    ${NC}"
echo "${CYAN}=====================================${NC}"
echo ""

# 检查 .env 文件
if [ ! -f "config/.env" ]; then
    echo "${YELLOW}[!] config/.env not found. Copying from .env.example...${NC}"
    cp config/.env.example config/.env
    echo "${RED}[!] Please fill in your ANTHROPIC_API_KEY in config/.env before continuing${NC}"
    exit 1
fi

# 启动后端
echo "${GREEN}[1/2] Starting backend server...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

sleep 2
echo "${GREEN}Backend running at http://localhost:8000${NC}"

# 启动前端
echo "${GREEN}[2/2] Starting frontend...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install -q
fi
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "${GREEN}✓ Game ready!${NC}"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# 等待并清理
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT
wait
