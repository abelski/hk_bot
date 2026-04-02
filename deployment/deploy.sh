#!/bin/bash
# Deploy to Proxmox LXC Container

set -e

CONTAINER_NAME="hk-telegram-bot"
CONTAINER_ID=100
STORAGE="local"

echo "🚀 Starting deployment to Proxmox..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if container exists
if pvesh get /nodes/$(hostname) | grep -q "\"vmid\":$CONTAINER_ID"; then
    echo -e "${YELLOW}Container already exists. Removing...${NC}"
    pct destroy $CONTAINER_ID
fi

echo -e "${GREEN}Creating new container...${NC}"
pct create $CONTAINER_ID \
    --hostname $CONTAINER_NAME \
    --cores 2 \
    --memory 1024 \
    --rootfs $STORAGE:32 \
    --net0 name=eth0,bridge=vmbr0 \
    debian-12-standard

echo -e "${GREEN}Starting container...${NC}"
pct start $CONTAINER_ID

# Wait for container to start
sleep 5

echo -e "${GREEN}Installing dependencies...${NC}"
pct exec $CONTAINER_ID -- apt-get update
pct exec $CONTAINER_ID -- apt-get install -y python3 python3-pip git

# Copy files to container
echo -e "${GREEN}Copying application files...${NC}"
pct push $CONTAINER_ID requirements.txt /root/requirements.txt
pct push $CONTAINER_ID src/ /root/src/
pct push $CONTAINER_ID proxmox_mcp/ /root/proxmox_mcp/
pct push $CONTAINER_ID .env /root/.env

echo -e "${GREEN}Installing Python dependencies...${NC}"
pct exec $CONTAINER_ID -- pip install -r /root/requirements.txt

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${YELLOW}Container ID: $CONTAINER_ID${NC}"
echo ""
echo "To start the bot in the container, run:"
echo "  pct exec $CONTAINER_ID -- python /root/src/bot.py"
