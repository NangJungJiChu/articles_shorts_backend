#!/bin/bash
REPO_URL="https://github.com/NangJungJiChu/articles_shorts_backend.git"
PROJECT_DIR="/home/ubuntu/articles_shorts_backend"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
MANAGE_PY="$PROJECT_DIR/manage.py"

sudo apt update
sudo apt install -y git python3-pip curl
cd /home/ubuntu
git clone "$REPO_URL" "$PROJECT_DIR"
chown -R ubuntu:ubuntu /home/ubuntu/articles_shorts_backend
cd "$PROJECT_DIR"

cat << EOF > .env
AWS_ACCESS_KEY_ID=abcd1234
AWS_SECRET_ACCESS_KEY=abcd1234
DB_PASSWORD=abcd1234
DB_HOST=1.2.3.4
OPENSEARCH_USER=adminabcd
OPENSEARCH_PASSWORD=Qwer1234!!
OPENSEARCH_PORT=443
OPENSEARCH_HOST=vpc-localhost-test
EOF

curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/bin" sh
uv sync

(crontab -l 2>/dev/null; echo "*/30 * * * * /home/ubuntu/articles_shorts_backend/.venv/bin/python /home/ubuntu/articles_shorts_backend/manage.py run_recsys_training >> /home/ubuntu/articles_shorts_backend/cron.log 2>&1") | crontab -

cat << EOF > /etc/systemd/system/njjc-qcluster.service 

[Unit]
Description=Django QCluster
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/articles_shorts_backend
ExecStart=/home/ubuntu/articles_shorts_backend/.venv/bin/python /home/ubuntu/articles_shorts_backend/manage.py qcluster
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat << EOF > /etc/systemd/system/njjc-runserver.service
[Unit]
Description=Django Runserver
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/articles_shorts_backend
ExecStart=/home/ubuntu/articles_shorts_backend/.venv/bin/python /home/ubuntu/articles_shorts_backend/manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable njjc-runserver njjc-qcluster
sudo systemctl restart njjc-runserver njjc-qcluster