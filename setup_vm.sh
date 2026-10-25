#!/bin/bash
# JobTruth VM Setup — run this once inside Ubuntu VM
# Usage: bash setup_vm.sh
# Then open: http://127.0.0.1:8000

set -e
echo ""
echo "========================================="
echo "  JobTruth VM Setup"
echo "========================================="

# 1. Install system deps
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git curl

# 2. Clone or update repo
echo "[2/5] Getting latest code from GitHub..."
if [ -d "$HOME/jobtruth" ]; then
    cd "$HOME/jobtruth"
    git pull --rebase origin main
else
    git clone https://github.com/ritzs04/jobtruth.git "$HOME/jobtruth"
    cd "$HOME/jobtruth"
fi

# 3. Python virtualenv + deps
echo "[3/5] Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4. Write .env
# The analyze, headers, and company-verify tabs work WITHOUT credentials.
# Only file upload needs AWS. You can fill in the real values from your Windows
# .env file if you want upload to work during the demo.
echo "[4/5] Writing .env file..."
cat > .env << 'ENVEOF'
S3_BUCKET=jobtruth-1792916538
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
JWT_SECRET_KEY=jobtruth-dev-secret-2024
HMAC_SECRET=jobtruth-hmac-secret-2024
ENVEOF
echo ""
echo "  NOTE: Replace YOUR_ACCESS_KEY_ID and YOUR_SECRET_ACCESS_KEY in .env"
echo "  if you want the file-upload demo to work. Otherwise all other tabs work fine."
echo ""

# 5. Start server
echo "[5/5] Starting server..."
echo ""
echo "========================================="
echo "  App is starting at http://127.0.0.1:8000"
echo "  Open Firefox in VM -> http://127.0.0.1:8000"
echo "  Press Ctrl+C to stop"
echo "========================================="
echo ""
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
