# Core Nexus

Production-ready monorepo with TypeScript and Python packages, enforcing identical local/CI behavior and shipping signed SLSA-3 artifacts.

## 🚀 Features

### Modern Monorepo Architecture
- **Yarn 4 Zero-Install**: Committed `.yarn/` directory for reproducible builds
- **Poetry Workspace**: Python package management with lockfile dependency resolution
- **Cross-language CI/CD**: Unified workflows for TypeScript and Python packages
- **SLSA-3 Security**: Signed artifacts with provenance and SBOM generation

### Development Experience
- **Pre-commit Hooks**: Automated code quality checks with conventional commits
- **DevContainer**: Optimized for sub-60s GitHub Codespaces boot time
- **Makefile Interface**: Single source of truth for all build commands
- **Hot Reloading**: Fast development cycles with watch mode support

### Production Pipeline
- **Multi-stage CI**: Matrix builds for Node 18/20 and Python 3.9-3.12
- **Security Scanning**: Dependabot with intelligent auto-merge
- **Artifact Signing**: Cosign keyless signing with GitHub OIDC
- **Supply Chain**: CycloneDX SBOM and SLSA-3 provenance generation

## 📦 Packages

### TypeScript (`packages/`)
- **example-lib**: User management library with comprehensive test suite
  - Modern TypeScript with strict type checking
  - Vitest testing framework with coverage reporting
  - tsup bundler for ESM/CJS dual output
  - ESLint 9 with TypeScript integration

### Python (`python/`)
- **example-service**: FastAPI microservice with user management API
  - Pydantic v2 models with validation
  - Async service architecture
  - Comprehensive test coverage with pytest
  - ruff + black code formatting

## 🛠 Development

### Prerequisites
- Node.js 18+ (with Corepack enabled)
- Python 3.10+
- Poetry 1.8+

### Quick Start
```bash
# Install all dependencies
make install

# Run linting and tests
make ci

# Development mode
yarn dev          # TypeScript watch mode
poetry run pytest --watch  # Python test watch
```

### Commands
```bash
make install      # Install Yarn + Poetry dependencies
make lint         # Run ESLint + ruff linting
make test         # Run Vitest + pytest tests
make ci           # Full CI pipeline (install + lint + test)
make docker       # Build Docker container
```

## 🏗 Architecture

### Directory Structure
```
core-nexus/
├── .github/
│   ├── workflows/         # CI/CD pipelines
│   └── dependabot.yml     # Dependency automation
├── .devcontainer/         # GitHub Codespaces configuration
├── packages/              # TypeScript workspace packages
│   └── example-lib/       # Example TypeScript library
├── python/                # Python workspace packages
│   └── example-service/   # Example FastAPI service
├── tools/                 # Build scripts and utilities
├── Makefile              # Development commands
├── package.json          # Yarn workspace root
└── pyproject.toml        # Poetry workspace root
```

### CI/CD Workflows

#### Development Workflows
- **node-ci.yml**: Triggered on `packages/**` changes
- **py-ci.yml**: Triggered on `python/**` changes
- **reusable-test.yml**: Shared workflow for environment setup

#### Release Workflow
- **release.yml**: Triggered on `v*` tags
  - Multi-platform Docker builds
  - Python wheel generation  
  - CycloneDX SBOM creation
  - Cosign artifact signing
  - SLSA-3 provenance generation
  - GHCR + PyPI publishing

### Security Features
- **Immutable Runners**: GitHub-hosted runners with ephemeral environments
- **Keyless Signing**: Cosign with GitHub OIDC (no stored secrets)
- **SLSA-3 Provenance**: Verifiable build metadata
- **SBOM Generation**: Software Bill of Materials for supply chain visibility
- **Dependabot Auto-merge**: Automated security and patch updates

## 🔐 Security & Compliance

### Supply Chain Security
- All dependencies tracked in lockfiles (`yarn.lock`, `poetry.lock`)
- Pre-commit hooks prevent credential leakage
- Automated vulnerability scanning via Dependabot
- Signed releases with verifiable provenance

### SLSA-3 Compliance
- Hermetic builds on GitHub-hosted runners
- Provenance generation via `slsa-github-generator`
- Artifact signing with Cosign keyless mode
- Supply chain metadata attached to releases

## 📋 Requirements Met

✅ **Yarn 4 Zero-Install**: Committed `.yarn/` with PnP linker  
✅ **Poetry Monorepo**: Python workspace with shared dev dependencies  
✅ **Identical Local/CI**: Makefile ensures `make ci` works everywhere  
✅ **Pre-commit Hooks**: ESLint+Prettier, ruff+black, conventional commits  
✅ **Matrix CI**: Node 18/20, Python 3.9-3.12 testing  
✅ **SLSA-3 Artifacts**: Docker + wheel signing with provenance  
✅ **GitHub Integration**: Dependabot auto-merge, GHCR/PyPI publishing  
✅ **Fast Codespaces**: Sub-60s boot with optimized devcontainer  

## 🚀 Getting Started

1. **Clone and setup**:
   ```bash
   git clone https://github.com/Von-Base-Enterprises/core-nexus.git
   cd core-nexus
   make install
   ```

2. **Verify pipeline**:
   ```bash
   make ci  # Should pass all linting and tests
   ```

3. **Development workflow**:
   ```bash
   # Work on TypeScript package
   cd packages/example-lib
   yarn dev
   
   # Work on Python service  
   cd python/example-service
   poetry run python -m example_service.main
   ```

4. **Create release**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   # Triggers SLSA-3 release workflow
   ```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with Claude Code** - Production-ready monorepo template for modern TypeScript and Python development.