# Deploy Tool

A powerful deployment tool for ML models and algorithms, designed to simplify the packaging, publishing, and deployment of machine learning projects.

## Features

- **Component-based Management**: Separate packaging and publishing for flexible version control
- **Type-agnostic Design**: Define your own component types (model, config, runtime, etc.)
- **Git-driven Workflow**: All configurations and manifests are managed through Git
- **Path Management**: Project-root based path resolution for consistency and portability
- **Multiple Compression Algorithms**: Support for gzip, bzip2, xz, lz4
- **Progress Tracking**: Real-time progress display with Rich library
- **Flexible Storage Backends**: Support for local filesystem, BOS, S3 (extensible)

## Quick Start

### Installation

```bash
# Install from wheel package (internal distribution)
pip install --user deploy_tool-1.0.0-py3-none-any.whl

# Verify installation
deploy-tool --version
# or
python -m deploy_tool --version
```

### Basic Usage

#### 1. Initialize a project

```bash
# Interactive mode - will prompt for project details
deploy-tool init

# Initialize with project name
deploy-tool init --name "My Algorithm Project"
# or use short option
deploy-tool init -n "My Algorithm Project"

# Initialize with all options (skip interactive mode)
deploy-tool init -n "My Project" -t algorithm -d "My awesome ML algorithm"

# Initialize in a new directory
deploy-tool init ./my-new-project

# Force initialization in non-empty directory
deploy-tool init --force
# or
deploy-tool init -f

# Skip git initialization
deploy-tool init --no-git
```

**Available options for `init` command:**
- `-n, --name`: Project name
- `-t, --type`: Project type (choices: `algorithm`, `model`, `service`, `general`, default: `algorithm`)
- `-d, --description`: Project description
- `-f, --force`: Force initialization even if directory is not empty
- `--no-git`: Skip git repository initialization

The initialization process creates:
- `.deploy-tool.yaml` - Project configuration file
- `deployment/` - Directory structure for deployment artifacts
- `.gitignore` - Git ignore rules with sensible defaults
- `src/` - Source code directory
- `dist/` - Output directory for packaged components

#### 2. Package components

```bash
# Auto mode (recommended) - must specify type and version
deploy-tool pack ./models --auto --type model --version 1.0.1

# Package different component types
deploy-tool pack ./configs --auto --type config --version 1.0.0
deploy-tool pack ./runtime --auto --type python-runtime --version 3.10.12
```

#### 3. Publish components

```bash
# Publish multiple components as a release
deploy-tool publish \
  --component model:1.0.1 \
  --component config:1.0.0 \
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

### Component Types

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

### Project Structure

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI
- Beautiful terminal output with [Rich](https://rich.readthedocs.io/)
- Compression support via Python's standard library and optional LZ4