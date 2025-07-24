#!/bin/bash
set -e

echo "🔧 Setting up Core Nexus development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Update package lists
print_status "Updating package lists..."
sudo apt-get update -qq

# Install essential packages for performance
print_status "Installing performance tools..."
sudo apt-get install -y -qq \
    build-essential \
    curl \
    wget \
    unzip \
    jq \
    htop \
    tree \
    make \
    git-lfs \
    ca-certificates \
    gnupg \
    lsb-release

# Install Corepack and enable it
print_status "Setting up Corepack..."
sudo corepack enable || {
    print_warning "Corepack not available, installing manually..."
    sudo npm install -g corepack
    sudo corepack enable
}

# Install Poetry
print_status "Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/home/vscode/.local/bin:$PATH"
    echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.bashrc
    echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.zshrc
else
    print_success "Poetry already installed"
fi

# Configure Poetry for performance
print_status "Configuring Poetry..."
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true
poetry config installer.parallel true
poetry config installer.max-workers 10

# Configure Git (if not already configured)
if [ -z "$(git config --global user.name)" ]; then
    print_status "Configuring Git..."
    git config --global user.name "Codespace User"
    git config --global user.email "codespace@vonbase.com"
    git config --global init.defaultBranch main
    git config --global pull.rebase false
    git config --global core.autocrlf input
fi

# Set up directory structure for caching
print_status "Setting up cache directories..."
mkdir -p /home/vscode/.cache/pypoetry
mkdir -p /home/vscode/.yarn/cache
mkdir -p /home/vscode/.npm
mkdir -p /workspaces/core-nexus/.devcontainer/node_modules-cache
mkdir -p /workspaces/core-nexus/.devcontainer/poetry-cache

# Set correct ownership
sudo chown -R vscode:vscode /home/vscode/.cache
sudo chown -R vscode:vscode /home/vscode/.yarn
sudo chown -R vscode:vscode /home/vscode/.npm
sudo chown -R vscode:vscode /home/vscode/.local

# Configure npm for performance
print_status "Configuring npm..."
npm config set cache /home/vscode/.npm
npm config set progress false
npm config set fund false
npm config set audit false

# Pre-warm package managers (if package files exist)
if [ -f "/workspaces/core-nexus/package.json" ]; then
    print_status "Pre-warming Yarn cache..."
    cd /workspaces/core-nexus
    yarn config set enableGlobalCache false
    yarn config set cacheFolder /home/vscode/.yarn/cache
fi

if [ -f "/workspaces/core-nexus/pyproject.toml" ]; then
    print_status "Pre-warming Poetry cache..."
    cd /workspaces/core-nexus
    poetry config cache-dir /home/vscode/.cache/pypoetry
fi

# Install GitHub CLI completions
print_status "Setting up GitHub CLI..."
if command -v gh &> /dev/null; then
    gh completion -s zsh > /home/vscode/.oh-my-zsh/completions/_gh 2>/dev/null || true
fi

# Configure zsh with useful aliases
print_status "Setting up shell aliases..."
cat >> /home/vscode/.zshrc << 'EOF'

# Core Nexus aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'

# Development aliases
alias m='make'
alias mi='make install'
alias mt='make test'
alias ml='make lint'
alias mc='make ci'
alias mh='make help'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias gb='git branch'
alias gco='git checkout'

# Python aliases
alias py='python'
alias poe='poetry'
alias ptest='poetry run pytest'
alias pruff='poetry run ruff'
alias pblack='poetry run black'

# Yarn aliases
alias y='yarn'
alias yl='yarn lint'
alias yt='yarn test'
alias yb='yarn build'
alias yd='yarn dev'

# Docker aliases
alias d='docker'
alias dc='docker-compose'
alias dps='docker ps'
alias di='docker images'

# Quick navigation
alias workspace='cd /workspaces/core-nexus'
alias w='cd /workspaces/core-nexus'
EOF

# Set up VS Code workspace settings
print_status "Creating VS Code workspace configuration..."
mkdir -p /workspaces/core-nexus/.vscode
cat > /workspaces/core-nexus/.vscode/settings.json << 'EOF'
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "eslint.workingDirectories": ["packages/*"],
  "typescript.preferences.importModuleSpecifier": "relative",
  "files.associations": {
    "*.toml": "toml",
    "Makefile": "makefile",
    "*.mk": "makefile"
  },
  "search.exclude": {
    "**/.yarn": true,
    "**/.venv": true,
    "**/node_modules": true,
    "**/__pycache__": true
  }
}
EOF

# Create launch configuration for debugging
cat > /workspaces/core-nexus/.vscode/launch.json << 'EOF'
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Python: pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${workspaceFolder}"],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    }
  ]
}
EOF

# Install pre-commit hooks if available
if [ -f "/workspaces/core-nexus/.pre-commit-config.yaml" ]; then
    print_status "Installing pre-commit hooks..."
    cd /workspaces/core-nexus
    poetry run pre-commit install 2>/dev/null || print_warning "Pre-commit not available yet"
fi

# Clean up package cache to reduce image size
print_status "Cleaning up..."
sudo apt-get autoremove -y -qq
sudo apt-get autoclean -y -qq

print_success "🎉 Core Nexus development environment setup complete!"
print_status "💡 Tips:"
echo "  - Run 'make help' to see available commands"
echo "  - Use 'w' alias to quickly navigate to workspace"
echo "  - Git is pre-configured for development"
echo "  - All package managers are optimized for performance"
echo ""
print_success "Happy coding! 🚀"