# Multi-stage Dockerfile for optimized devcontainer
FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04 as base

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive
ENV FORCE_COLOR=1
ENV CI=false

# Create cache directories early for better layer caching
RUN mkdir -p /home/vscode/.cache/pypoetry \
    && mkdir -p /home/vscode/.yarn/cache \
    && mkdir -p /home/vscode/.npm \
    && chown -R vscode:vscode /home/vscode/.cache \
    && chown -R vscode:vscode /home/vscode/.yarn \
    && chown -R vscode:vscode /home/vscode/.npm

# Stage for Node.js and Yarn pre-caching
FROM base as node-cache

# Install Node.js 20 and enable Corepack
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && corepack enable \
    && npm config set cache /home/vscode/.npm \
    && npm config set progress false \
    && npm config set fund false \
    && npm config set audit false

# Pre-install common packages for faster startup
RUN npm install -g \
    typescript@latest \
    @types/node@latest \
    eslint@latest \
    prettier@latest \
    vitest@latest

# Stage for Python and Poetry pre-caching
FROM node-cache as python-cache

# Install Python 3.10 and pip
RUN apt-get update \
    && apt-get install -y \
        python3.10 \
        python3.10-dev \
        python3.10-venv \
        python3-pip \
        python3-setuptools \
        python3-wheel \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && echo 'export PATH="/root/.local/bin:$PATH"' >> /etc/bash.bashrc

# Configure Poetry for performance
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry config installer.parallel true \
    && poetry config installer.max-workers 10

# Pre-install common Python packages
RUN pip3 install --no-cache-dir \
    wheel \
    setuptools \
    pip-tools \
    black \
    ruff \
    mypy \
    pytest \
    pytest-cov

# Final stage with optimizations
FROM python-cache as final

# Install additional development tools
RUN apt-get update \
    && apt-get install -y \
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
        lsb-release \
        zsh \
        fish \
    && apt-get autoremove -y \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh

# Set up zsh as default shell for vscode user
RUN chsh -s /bin/zsh vscode

# Create workspace directory
RUN mkdir -p /workspaces/core-nexus \
    && chown -R vscode:vscode /workspaces/core-nexus

# Switch to vscode user
USER vscode

# Install Oh My Zsh
RUN sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" || true

# Pre-configure git
RUN git config --global init.defaultBranch main \
    && git config --global pull.rebase false \
    && git config --global core.autocrlf input

# Set up environment variables in shell profiles
RUN echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.bashrc \
    && echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.zshrc \
    && echo 'export FORCE_COLOR=1' >> /home/vscode/.bashrc \
    && echo 'export FORCE_COLOR=1' >> /home/vscode/.zshrc

# Set working directory
WORKDIR /workspaces/core-nexus

# Keep container running
CMD ["sleep", "infinity"]