#!/bin/bash
# Quick test script to verify all components before bulk run

set -e

cd "$(dirname "$0")"

echo "=== Chatlee.io Farmer Test ==="
echo

echo "1. Checking Python syntax..."
python3 -m py_compile main.py api.py solver.py emailnator.py
echo "   ✓ All Python files valid"
echo

echo "2. Checking configuration..."
python3 -c "import json; config=json.load(open('config.json')); print(f\"   ✓ Config loaded: {config['chatlee_api']['base_url']}\")"
echo

echo "3. Checking dependencies..."
python3 -c "import requests; print('   ✓ requests installed')"
python3 -c "from bs4 import BeautifulSoup; print('   ✓ beautifulsoup4 installed')"
echo

echo "4. Testing local Turnstile solver..."
SOLVER_STATUS=$(curl -s http://127.0.0.1:8003/health 2>&1 || echo "NOT_RUNNING")
if [[ "$SOLVER_STATUS" == *"ok"* ]] || [[ "$SOLVER_STATUS" == *"healthy"* ]]; then
    echo "   ✓ Local solver responding at :8003"
else
    echo "   ⚠ Local solver not responding (start it before running)"
fi
echo

echo "5. Testing Emailnator.com connectivity..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://www.emailnator.com 2>&1 || echo "000")
if [[ "$STATUS" == "200" ]]; then
    echo "   ✓ Emailnator.com reachable"
else
    echo "   ⚠ Emailnator.com returned HTTP $STATUS"
fi
echo

echo "6. Testing Chatlee.io connectivity..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://chatlee.io 2>&1 || echo "000")
if [[ "$STATUS" == "200" ]]; then
    echo "   ✓ Chatlee.io reachable"
else
    echo "   ⚠ Chatlee.io returned HTTP $STATUS"
fi
echo

echo "=== Test Complete ==="
echo
echo "To run the farmer:"
echo "  python3 main.py --ref-url 'https://chatlee.io/?inv=YOUR_CODE' --count 5"
echo
