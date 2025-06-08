#!/bin/bash
# Docker Installation Guide for WSL/Linux

echo "🐳 Docker Installation Guide for Core Nexus Memory Service"
echo "========================================================"
echo ""

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "✅ Docker is already installed!"
    docker --version
    
    if command -v docker-compose &> /dev/null; then
        echo "✅ Docker Compose is already installed!"
        docker-compose --version
        echo ""
        echo "🚀 Ready to run: ./step1_deploy.sh"
        exit 0
    fi
fi

echo "Installing Docker and Docker Compose in WSL/Linux..."
echo ""

# Update package manager
echo "📦 Updating package manager..."
sudo apt-get update

# Install prerequisites
echo "📦 Installing prerequisites..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
echo "🔑 Adding Docker GPG key..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up Docker repository
echo "📂 Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
echo "📦 Updating package index..."
sudo apt-get update

# Install Docker Engine
echo "🐳 Installing Docker Engine..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
echo "👤 Adding user to docker group..."
sudo usermod -aG docker $USER

# Start Docker service
echo "🚀 Starting Docker service..."
sudo service docker start

# Test Docker installation
echo "🧪 Testing Docker installation..."
if sudo docker run hello-world; then
    echo "✅ Docker installation successful!"
else
    echo "❌ Docker installation failed!"
    exit 1
fi

# Test Docker Compose
echo "🧪 Testing Docker Compose..."
if docker-compose --version; then
    echo "✅ Docker Compose installation successful!"
else
    echo "❌ Docker Compose installation failed!"
    exit 1
fi

echo ""
echo "🎉 Docker installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Log out and log back in (or run: newgrp docker)"
echo "2. Run: ./step1_deploy.sh"
echo ""
echo "🔧 Troubleshooting:"
echo "- If permission denied: sudo service docker start"
echo "- If group issues: newgrp docker"
echo "- Check status: sudo service docker status"