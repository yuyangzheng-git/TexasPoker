#!/bin/bash
# 运行所有后端测试

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
pip install pytest -q

cd ../tests
echo ""
echo "${GREEN}Test: Hand Evaluator${NC}"
python3 -m pytest test_hand_evaluator.py -v

echo ""
echo "${GREEN}Test: Side Pots${NC}"
python3 -m pytest test_side_pot.py -v

echo ""
echo "${GREEN}All tests completed!${NC}"
