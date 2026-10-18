#!/bin/bash
# 运行所有后端测试
# 用法: ./run_tests.sh   （在仓库根目录执行）

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "${CYAN}Running backend tests...${NC}"
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt pytest -q

cd ../tests
echo ""
echo "${GREEN}All test files:${NC}"
python3 -m pytest -v

echo ""
echo "${GREEN}All tests completed!${NC}"
