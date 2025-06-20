# Deploy Tool

A powerful deployment tool for ML models and algorithms, designed to simplify the packaging, publishing, and deployment of machine learning projects.

## Features

- **Component-based Management**: Separate packaging and publishing for flexible version control
- **Type-agnostic Design**: Define your own component types (model, config, runtime, etc.)
- **Git-driven Workflow**: All configurations and manifests are managed through Git
- **Path Management**: Project-root based path resolution for consistency and portability
<<<<<<< HEAD
- **Multiple Publishing Methods**: Filesystem (manual transfer), S3, BOS (automatic transfer)
- **Smart Directory Mapping**: Maintains consistent paths between development and deployment

## Table of Contents

- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Basic Workflow](#basic-workflow)
- [Understanding the Workflow](#understanding-the-workflow)
  - [Publishing Methods](#publishing-methods)
  - [Directory Structure Mapping](#directory-structure-mapping)
  - [Git Integration](#git-integration)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
=======
- **Multiple Compression Algorithms**: Support for gzip, bzip2, xz, lz4
- **Progress Tracking**: Real-time progress display with Rich library
- **Flexible Storage Backends**: Support for local filesystem, BOS, S3 (extensible)
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

## Quick Start

### Installation

```bash
# Install from PyPI
pip install deploy-tool

# Install from wheel package
pip install deploy_tool-1.0.0-py3-none-any.whl

# Verify installation
deploy-tool --version
```

### Basic Workflow

Let's walk through a complete example of packaging, publishing, and deploying a machine learning project.

#### 1. Initialize a project

First, create a new project with the standard directory structure:

```bash
# Create a new project
deploy-tool init --name "my-ml-project" --type algorithm

# This creates:
# .deploy-tool.yaml      - Project configuration (marks project root)
# deployment/           - Deployment artifacts directory
# src/                  - Source code (managed by Git)
# dist/                 - Package output (Git ignored)
```

**What happens during initialization:**
- Creates a `.deploy-tool.yaml` file that identifies your project root
- Sets up the standard directory structure
- Initializes Git repository (unless `--no-git` is specified)
- Creates a `.gitignore` with sensible defaults

<<<<<<< HEAD
**Project structure after initialization:**
```
my-ml-project/
├── .deploy-tool.yaml     # Project configuration
├── .gitignore           # Git ignore rules
├── deployment/          # Deployment artifacts
│   ├── manifests/      # Component manifests (Git tracked)
│   ├── releases/       # Release manifests (Git tracked)
│   └── package-configs/ # Packaging configurations
├── src/                # Your source code
└── dist/               # Package outputs (Git ignored)
```

#### 2. Package components

When you have model files, configurations, or runtime environments to deploy, package them as components:

=======
The initialization process creates:
- `.deploy-tool.yaml` - Project configuration file
- `deployment/` - Directory structure for deployment artifacts
- `.gitignore` - Git ignore rules with sensible defaults
- `src/` - Source code directory
- `dist/` - Output directory for packaged components

#### 2. Package components

>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
```bash
# Package your model files
deploy-tool pack ./models --auto --type model --version 1.0.0

<<<<<<< HEAD
# Package configuration files  
=======
# Package different component types
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
deploy-tool pack ./configs --auto --type config --version 1.0.0

# Package runtime environment
deploy-tool pack ./runtime --auto --type runtime --version 3.10.0
```

<<<<<<< HEAD
**What happens during packaging:**
1. **Scans** the specified directory
2. **Creates** a compressed archive in `dist/` directory
3. **Generates** a manifest file in `deployment/manifests/`
4. **Shows** Git commands to track the manifest

**Example output:**
```
✓ Scanning directory: ./models
✓ Found 15 files (245.3 MB total)
✓ Creating package: dist/model-1.0.0.tar.gz
✓ Generating manifest: deployment/manifests/model-1.0.0.manifest.json

📝 Next steps:
1. Track the manifest in Git:
   git add deployment/manifests/model-1.0.0.manifest.json
   git commit -m "Add model v1.0.0 manifest"
   
2. The package file (dist/model-1.0.0.tar.gz) is NOT tracked by Git
```

**Important:** Each component is packaged separately, allowing independent versioning and updates.

#### 3. Publish components

Publishing prepares your components for deployment. The default method is **filesystem**, which requires manual file transfer.

=======
#### 3. Publish components

>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
```bash
# Publish with filesystem method (default)
deploy-tool publish \
  --component model:1.0.0 \
  --component config:1.0.0 \
<<<<<<< HEAD
  --component runtime:3.10.0 \
  --release-version 2024.01.20 \
  --method filesystem
```

**What happens during publishing:**
1. **Creates** a release directory structure
2. **Copies** packaged files to the release directory
3. **Generates** a release manifest
4. **Provides** detailed transfer instructions

**Example output:**
```
✓ Release created: 2024.01.20
✓ Published to: deployment/releases/2024.01.20/
  
📁 Directory structure:
deployment/releases/2024.01.20/
├── model/
│   └── 1.0.0/
│       └── model-1.0.0.tar.gz
├── config/
│   └── 1.0.0/
│       └── config-1.0.0.tar.gz
└── runtime/
    └── 3.10.0/
        └── runtime-3.10.0.tar.gz

📋 Next steps for filesystem publishing:
1. Add release manifest to Git:
   git add deployment/releases/2024.01.20.release.json
   git commit -m "Release version 2024.01.20"
   git push

2. Transfer the published files to your deployment server:
   # Option A: Using rsync (recommended for large files)
   rsync -avz deployment/releases/2024.01.20/ user@server:/opt/deployments/releases/2024.01.20/
   
   # Option B: Using scp
   scp -r deployment/releases/2024.01.20/ user@server:/opt/deployments/releases/
   
   # Option C: Using shared storage
   cp -r deployment/releases/2024.01.20/ /mnt/shared/deployments/releases/

3. On the deployment server, ensure the files are in:
   /opt/deployments/releases/2024.01.20/
```

**Alternative publishing methods with automatic transfer:**

```bash
# Publish to S3 (automatic upload)
deploy-tool publish \
  --component model:1.0.0 \
  --component config:1.0.0 \
  --release-version 2024.01.20 \
  --method s3 \
  --bucket my-ml-releases

# Publish to Baidu Object Storage (automatic upload)
deploy-tool publish \
  --component model:1.0.0 \
  --release-version 2024.01.20 \
  --method bos \
  --bucket my-bos-bucket
```

With S3 or BOS methods, files are automatically uploaded and no manual transfer is needed.

#### 4. Deploy a release

Deployment extracts published components to the target environment. The tool handles directory structure mapping automatically.

```bash
# Deploy from filesystem (requires manual transfer first)
deploy-tool deploy \
  --release 2024.01.20 \
  --target /opt/ml-apps/my-project \
  --method filesystem \
  --releases-dir /opt/deployments/releases
```

**What happens during deployment:**
1. **Reads** the release manifest to identify components
2. **Extracts** each component to versioned directories
3. **Creates** symbolic links to maintain path consistency
4. **Verifies** the deployment integrity

**Result structure:**
```
/opt/ml-apps/my-project/
├── model -> releases/2024.01.20/model/1.0.0/      # Symlink to current version
├── config -> releases/2024.01.20/config/1.0.0/    # Symlink to current version
├── runtime -> releases/2024.01.20/runtime/3.10.0/ # Symlink to current version
└── releases/
    └── 2024.01.20/
        ├── model/
        │   └── 1.0.0/
        │       └── [extracted model files]
        ├── config/
        │   └── 1.0.0/
        │       └── [extracted config files]
        └── runtime/
            └── 3.10.0/
                └── [extracted runtime files]
```
=======
  --component python-runtime:3.10.12 \
  --release-version 2024.01.20
```

#### 4. Deploy a release

```bash
# Deploy a specific release version
deploy-tool deploy --release 2024.01.20

# Deploy to specific target
deploy-tool deploy --release 2024.01.20 --target production
```

## Core Concepts
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

**Why symbolic links?**
- Your code can use the same paths in development and production
- Easy version switching without code changes
- Clear visibility of which version is active

<<<<<<< HEAD
**Deploy from cloud storage (automatic download):**

```bash
# Deploy from S3
deploy-tool deploy \
  --release 2024.01.20 \
  --target /opt/ml-apps/my-project \
  --method s3 \
  --bucket my-ml-releases

# Deploy from BOS
deploy-tool deploy \
  --release 2024.01.20 \
  --target /opt/ml-apps/my-project \
  --method bos \
  --bucket my-bos-bucket
```

## Understanding the Workflow

### Publishing Methods

The tool supports three publishing methods, each suited for different scenarios:

#### 1. Filesystem (Default)
- **How it works**: Published files remain on local filesystem
- **Transfer**: Manual (you control how files are moved)
- **Best for**: Development, testing, air-gapped environments
- **Advantages**: 
  - Full control over file transfer
  - Works in any environment
  - No external dependencies
- **Workflow**:
  ```
  Package → Publish (local) → Manual Transfer → Deploy
  ```
=======
Component types are completely user-defined. Common examples include:

- `model`: Model weights and files
- `config`: Configuration files
- `python-runtime`: Python environment
- `cuda-libs`: CUDA libraries
- `data`: Datasets
- Any custom type you need

### Manifests

Every packaging operation generates a manifest file that records:
- File checksums for integrity verification
- Component metadata (type, version, etc.)
- Relative paths for portability
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

#### 2. S3/BOS (Cloud Storage)
- **How it works**: Automatic upload during publish, automatic download during deploy
- **Transfer**: Automatic (tool handles everything)
- **Best for**: Production, multi-region deployment, CI/CD
- **Advantages**:
  - No manual file transfer needed
  - Centralized storage
  - Easy access from multiple locations
- **Workflow**:
  ```
  Package → Publish (upload) → Deploy (download)
  ```

<<<<<<< HEAD
### Directory Structure Mapping

The tool maintains consistent paths between development and deployment environments:

```
Development Structure:          Deployment Structure:
project-root/                   /deployment-target/
├── models/                     ├── model -> releases/x.x/model/1.0.0/
│   └── weights.pkl             │   └── weights.pkl
├── configs/                    ├── config -> releases/x.x/config/1.0.0/
│   └── settings.yaml           │   └── settings.yaml
└── runtime/                    └── runtime -> releases/x.x/runtime/3.10.0/
    └── requirements.txt            └── requirements.txt
```

This mapping ensures:
- **Code compatibility**: Same relative paths work everywhere
- **Version flexibility**: Easy switching between versions
- **Clear organization**: Visible version information

### Git Integration

The tool follows a Git-driven workflow for configuration management:

**What to commit:**
- ✅ `deployment/manifests/*.manifest.json` - Component manifests
- ✅ `deployment/releases/*.release.json` - Release manifests
- ✅ `.deploy-tool.yaml` - Project configuration
- ✅ Source code in `src/`

**What NOT to commit:**
- ❌ `dist/` - Packaged files (too large)
- ❌ `deployment/releases/*/` - Published packages (transfer separately)

**Example Git workflow:**
```bash
# After packaging
git add deployment/manifests/model-1.0.0.manifest.json
git commit -m "Add model v1.0.0 manifest"

# After publishing
git add deployment/releases/2024.01.20.release.json
git commit -m "Release version 2024.01.20"

git push origin main
```

## Advanced Usage

### Custom Component Types

Define any component type that makes sense for your project:

```bash
# Standard types
deploy-tool pack ./models --type model --version 1.0.0
deploy-tool pack ./configs --type config --version 1.0.0

# Custom types for your needs
deploy-tool pack ./preprocessing --type preprocessor --version 1.0.0
deploy-tool pack ./postprocessing --type postprocessor --version 1.0.0
deploy-tool pack ./evaluation --type evaluator --version 1.0.0
```

### Selective Deployment

Deploy only specific components when needed:

```bash
# Deploy only the model component
deploy-tool deploy --component model:1.0.0 --target /opt/ml-apps/test

# Update configuration without touching model
deploy-tool deploy --component config:1.1.0 --target /opt/ml-apps/prod
```

### Multi-Environment Management

Manage different environments with different releases:

```bash
# Development environment
deploy-tool deploy --release 2024.01.20-dev --target /opt/ml-apps/dev

# Staging environment  
deploy-tool deploy --release 2024.01.20-rc1 --target /opt/ml-apps/staging

# Production environment
deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod
```

### Version Switching

Switch between deployed versions easily:

```bash
# List available versions
deploy-tool version list --target /opt/ml-apps/prod

# Switch to a different version
deploy-tool version switch 2024.01.19 --target /opt/ml-apps/prod

# Roll back to previous version
deploy-tool version rollback --target /opt/ml-apps/prod
```

## Best Practices

### 1. Version Strategy

Choose appropriate versioning for each component type:

- **Models**: Semantic versioning (1.0.0, 1.1.0, 2.0.0)
  - Major: Architecture changes
  - Minor: Significant improvements
  - Patch: Bug fixes or minor tweaks

- **Configs**: Date-based or semantic
  - Date-based: 2024.01.20 for regular updates
  - Semantic: When config structure changes

- **Releases**: Date-based (2024.01.20) or semantic (v1.2.3)
  - Date-based: For regular deployment cycles
  - Semantic: For feature-based releases

### 2. Component Granularity

- **Keep components focused**: One responsibility per component
- **Separate by update frequency**: 
  - Frequently updated (models, configs)
  - Rarely updated (runtime, dependencies)
- **Use meaningful names**: `model`, `config`, not `stuff`, `misc`

### 3. File Transfer for Filesystem Publishing

Choose the appropriate transfer method based on your needs:

```bash
# For regular updates with large files
rsync -avz --progress deployment/releases/2024.01.20/ user@server:/opt/deployments/releases/

# For one-time transfers
scp -r deployment/releases/2024.01.20/ user@server:/opt/deployments/releases/

# For internal networks with shared storage
cp -r deployment/releases/2024.01.20/ /mnt/shared/deployments/releases/

# For version control (only for small packages)
git lfs track "deployment/releases/2024.01.20/*"
git add deployment/releases/2024.01.20/
git commit -m "Add release 2024.01.20 packages"
```

### 4. Deployment Safety

- **Always test first**: Deploy to development/staging before production
- **Use dry-run**: Preview changes before applying
  ```bash
  deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod --dry-run
  ```
- **Keep backups**: Previous releases for quick rollback
- **Monitor deployment**: Verify after deployment
  ```bash
  deploy-tool verify --release 2024.01.20 --target /opt/ml-apps/prod
  ```

## Troubleshooting

### Common Issues

**Q: Why use filesystem publishing instead of direct deployment?**

A: Filesystem publishing provides flexibility for:
- Air-gapped environments without internet access
- Custom transfer methods for security compliance
- Manual verification before deployment
- Bandwidth optimization with incremental transfers

**Q: How do I handle large model files?**

A: Optimize packaging for large files:
```bash
# Use lower compression for already-compressed files
deploy-tool pack ./models --type model --version 1.0.0 --compression gzip --level 1

# Or skip compression for binary files
deploy-tool pack ./models --type model --version 1.0.0 --compression none
```

**Q: Can I mix publishing methods?**

A: Yes, different components can use different methods:
```bash
# Large models to S3
deploy-tool publish --component model:1.0.0 --method s3 --bucket ml-models

# Small configs via filesystem
deploy-tool publish --component config:1.0.0 --method filesystem
```

**Q: How do I debug deployment issues?**

A: Use verbose mode and check logs:
```bash
# Enable debug output
deploy-tool deploy --release 2024.01.20 --target /opt/ml-apps/prod --verbose

# Check deployment status
deploy-tool status --target /opt/ml-apps/prod

# Verify file integrity
deploy-tool verify --release 2024.01.20 --target /opt/ml-apps/prod
```

### Error Messages

**"Project root not found"**
- Ensure you're in a project directory with `.deploy-tool.yaml`
- Or use `--project-root` to specify the location

**"Component not found"**
- Check if the manifest exists: `ls deployment/manifests/`
- Ensure you've committed and pulled the latest changes

**"Transfer failed"**
- For filesystem: Verify you've manually transferred the files
- For S3/BOS: Check your credentials and network connection
=======
```
project_root/
├── .deploy-tool.yaml      # Project configuration
├── src/                   # Source code (managed by Git)
├── models/                # Model files
├── configs/               # Configuration files
├── deployment/
│   ├── package-configs/   # Packaging configurations
│   ├── manifests/        # Component manifests (auto-generated)
│   └── releases/         # Release records (auto-generated)
├── dist/                 # Package output (Git ignored)
└── README.md
```

## Documentation

For detailed documentation, please refer to:
- [User Guide](docs/user_guide.md)
- [API Reference](docs/api_reference.md)
- [Architecture Design](docs/architecture.md)

## Development

### Setup development environment

```bash
# Clone repository
git clone https://github.com/yourteam/deploy-tool.git
cd deploy-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=deploy_tool

# Run specific test category
pytest -m "not slow"  # Skip slow tests
```
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)

### Code quality

```bash
# Format code
black deploy_tool tests
isort deploy_tool tests

# Lint code
flake8 deploy_tool tests
mypy deploy_tool

# Run all checks
tox
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

<<<<<<< HEAD
See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
=======
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI
- Beautiful terminal output with [Rich](https://rich.readthedocs.io/)
- Compression support via Python's standard library and optional LZ4
>>>>>>> parent of ea5206d (Refactor deployment logic to simplify component handling; improve error messages and enhance verification process)
