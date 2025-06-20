# Git Workflow Guide for Deploy Tool

This guide explains how to use Git effectively with the Deploy Tool for team collaboration and version control.

## Table of Contents

- [Overview](#overview)
- [What to Track in Git](#what-to-track-in-git)
- [Workflow Examples](#workflow-examples)
- [Team Collaboration](#team-collaboration)
- [Best Practices](#best-practices)
- [Integration with CI/CD](#integration-with-cicd)
- [Troubleshooting](#troubleshooting)

## Overview

The Deploy Tool uses Git as the source of truth for:
- Component manifests (what was packaged)
- Release manifests (what was published)
- Project configuration
- Source code

The actual packaged files are NOT stored in Git due to their size.

## What to Track in Git

### Always Commit ✅

```
.deploy-tool.yaml                    # Project configuration
deployment/manifests/*.manifest.json # Component manifests
deployment/releases/*.release.json   # Release manifests  
deployment/package-configs/*.yaml    # Packaging configurations
src/                                # Source code
```

### Never Commit ❌

```
dist/                    # Packaged files (too large)
deployment/releases/*/   # Published packages (use file transfer)
*.tar.gz, *.tar.bz2     # Any compressed packages
```

### Example .gitignore

```gitignore
# Deploy Tool specific
/dist/
/deployment/releases/*/
*.tar.gz
*.tar.bz2
*.tar.xz
*.tar.lz4

# Keep manifests and configs
!deployment/manifests/
!deployment/releases/*.release.json
!deployment/package-configs/
```

## Workflow Examples

### Basic Component Update

When updating a component (e.g., a new model version):

```bash
# 1. Package the new version
deploy-tool pack ./models --auto --type model --version 1.0.1

# 2. Check what was created
git status
# Output:
# Untracked files:
#   deployment/manifests/model-1.0.1.manifest.json
#   dist/model-1.0.1.tar.gz  (NOT tracked)

# 3. Add only the manifest
git add deployment/manifests/model-1.0.1.manifest.json

# 4. Commit with meaningful message
git commit -m "Add model v1.0.1 manifest - improved accuracy to 95%"

# 5. Push to share with team
git push origin main
```

### Creating a Release

When creating a release from multiple components:

```bash
# 1. Ensure you have latest manifests
git pull origin main

# 2. Create a release
deploy-tool publish \
  --component model:1.0.1 \
  --component config:1.0.0 \
  --component runtime:3.10.0 \
  --release-version 2024.01.20

# 3. Commit the release manifest
git add deployment/releases/2024.01.20.release.json
git commit -m "Release 2024.01.20: model v1.0.1, config v1.0.0, runtime v3.10.0"

# 4. Tag the release
git tag -a release-2024.01.20 -m "Production release 2024.01.20"

# 5. Push with tags
git push origin main --tags
```

### Hotfix Workflow

For emergency fixes:

```bash
# 1. Create hotfix branch from last release tag
git checkout -b hotfix/config-fix release-2024.01.20

# 2. Package the fix
deploy-tool pack ./configs --auto --type config --version 1.0.1

# 3. Commit the manifest
git add deployment/manifests/config-1.0.1.manifest.json
git commit -m "Fix config: correct database connection timeout"

# 4. Create hotfix release
deploy-tool publish \
  --component model:1.0.1 \      # Same model
  --component config:1.0.1 \     # Updated config
  --component runtime:3.10.0 \   # Same runtime
  --release-version 2024.01.20-hotfix1

# 5. Commit and tag
git add deployment/releases/2024.01.20-hotfix1.release.json
git commit -m "Hotfix release 2024.01.20-hotfix1"
git tag -a release-2024.01.20-hotfix1 -m "Hotfix for config timeout"

# 6. Merge to main
git checkout main
git merge --no-ff hotfix/config-fix
git push origin main --tags
```

## Team Collaboration

### Role-based Workflow

Different team members typically handle different components:

**Algorithm Engineer (Alice)**
```bash
# Works on model improvements
git checkout -b feature/model-v1.1
deploy-tool pack ./models --auto --type model --version 1.1.0
git add deployment/manifests/model-1.1.0.manifest.json
git commit -m "Model v1.1.0: add attention mechanism"
git push origin feature/model-v1.1
# Creates pull request for review
```

**Data Engineer (Bob)**
```bash
# Updates preprocessing configs
git checkout -b feature/new-preprocessing
deploy-tool pack ./configs --auto --type config --version 1.1.0
git add deployment/manifests/config-1.1.0.manifest.json
git commit -m "Config v1.1.0: add data normalization settings"
git push origin feature/new-preprocessing
# Creates pull request
```

**DevOps Engineer (Carol)**
```bash
# Reviews and creates releases
git checkout main
git pull origin main

# After PRs are merged, create release
deploy-tool publish \
  --component model:1.1.0 \
  --component config:1.1.0 \
  --component runtime:3.10.0 \
  --release-version 2024.01.21

git add deployment/releases/2024.01.21.release.json
git commit -m "Release 2024.01.21 with new model and config"
git tag -a release-2024.01.21 -m "Release with attention model"
git push origin main --tags
```

### Resolving Manifest Conflicts

When multiple people update the same component:

```bash
# If you get a conflict in manifests/
git pull origin main
# CONFLICT (add/add): Merge conflict in deployment/manifests/model-1.0.1.manifest.json

# Option 1: If versions should be different
# Rename your version
deploy-tool pack ./models --auto --type model --version 1.0.2
git add deployment/manifests/model-1.0.2.manifest.json
git rm deployment/manifests/model-1.0.1.manifest.json
git commit -m "Resolve conflict: use model v1.0.2"

# Option 2: If it's the same change
# Keep the existing manifest
git checkout --theirs deployment/manifests/model-1.0.1.manifest.json
git add deployment/manifests/model-1.0.1.manifest.json
git commit -m "Resolve conflict: use existing model v1.0.1"
```

## Best Practices

### 1. Commit Messages

Use clear, descriptive commit messages:

**Good examples:**
```
Add model v1.0.1 manifest - improved accuracy to 95%
Release 2024.01.20: model v1.0.1, config v1.0.0, runtime v3.10.0
Fix config v1.0.1: correct database timeout from 30s to 60s
Update runtime v3.10.1: add missing numpy dependency
```

**Bad examples:**
```
Update files
Fix
New version
asdf
```

### 2. Branch Strategy

```bash
main                    # Stable, production-ready
├── develop            # Integration branch
├── feature/*          # New features
├── hotfix/*          # Emergency fixes
└── release/*         # Release preparation
```

Example flow:
```bash
# Feature development
git checkout -b feature/new-model develop
# ... work ...
git push origin feature/new-model
# PR to develop

# Release preparation
git checkout -b release/2024.01.21 develop
# ... final testing ...
# PR to main
```

### 3. Tag Strategy

Use semantic versioning for tags:

```bash
# Release tags
git tag -a v1.2.0 -m "Release version 1.2.0"
git tag -a release-2024.01.20 -m "Production release 2024.01.20"

# Component tags (optional)
git tag -a model-v1.0.1 -m "Model version 1.0.1"
git tag -a config-v1.0.0 -m "Config version 1.0.0"
```

### 4. Pre-commit Hooks

Set up hooks to catch common issues:

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Check for large files
for file in $(git diff --cached --name-only); do
    if [[ $file == dist/* ]] || [[ $file == deployment/releases/*/* ]]; then
        echo "Error: Attempting to commit packaged files: $file"
        echo "Only commit manifest files, not the actual packages"
        exit 1
    fi
done

# Validate manifest JSON
for manifest in $(git diff --cached --name-only | grep -E '\.manifest\.json$'); do
    if ! python -m json.tool "$manifest" > /dev/null 2>&1; then
        echo "Error: Invalid JSON in $manifest"
        exit 1
    fi
done
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Package and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  package:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install deploy-tool
        run: pip install deploy-tool
        
      - name: Package components
        run: |
          deploy-tool pack ./models --auto --type model --version ${{ github.ref_name }}
          deploy-tool pack ./configs --auto --type config --version ${{ github.ref_name }}
          
      - name: Commit manifests
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add deployment/manifests/
          git commit -m "Add manifests for ${{ github.ref_name }}"
          git push
          
      - name: Create release
        run: |
          deploy-tool publish \
            --component model:${{ github.ref_name }} \
            --component config:${{ github.ref_name }} \
            --release-version ${{ github.ref_name }}
            
      - name: Upload packages
        uses: actions/upload-artifact@v3
        with:
          name: packages-${{ github.ref_name }}
          path: deployment/releases/${{ github.ref_name }}/
```

### GitLab CI Example

```yaml
stages:
  - package
  - publish
  - deploy

package:model:
  stage: package
  script:
    - deploy-tool pack ./models --auto --type model --version $CI_COMMIT_TAG
    - git add deployment/manifests/
    - git commit -m "CI: Add model manifest for $CI_COMMIT_TAG"
    - git push origin HEAD:main
  only:
    - tags

publish:release:
  stage: publish
  script:
    - |
      deploy-tool publish \
        --component model:$CI_COMMIT_TAG \
        --component config:$CI_COMMIT_TAG \
        --release-version $CI_COMMIT_TAG
    - git add deployment/releases/
    - git commit -m "CI: Create release $CI_COMMIT_TAG"
    - git push origin HEAD:main
  only:
    - tags

deploy:production:
  stage: deploy
  script:
    - |
      deploy-tool deploy \
        --release $CI_COMMIT_TAG \
        --target /opt/ml-apps/prod \
        --method s3 \
        --bucket $S3_BUCKET
  only:
    - tags
  when: manual
```

## Troubleshooting

### Common Git Issues

**"Manifest not found in Git"**
```bash
# Check if manifest was committed
git log --name-only | grep model-1.0.1.manifest.json

# If not found, check if it exists locally
ls deployment/manifests/model-1.0.1.manifest.json

# If exists but not committed
git add deployment/manifests/model-1.0.1.manifest.json
git commit -m "Add missing model v1.0.1 manifest"
```

**"Can't find release manifest"**
```bash
# Ensure you have latest changes
git pull origin main

# Check available releases
ls deployment/releases/*.release.json

# Check Git history
git log --oneline deployment/releases/
```

**"Accidentally committed large files"**
```bash
# If not pushed yet
git reset --soft HEAD~1
git reset HEAD dist/model-1.0.1.tar.gz
git commit -m "Your message without large file"

# If already pushed (requires force push - coordinate with team!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch dist/model-1.0.1.tar.gz' \
  --prune-empty --tag-name-filter cat -- --all
```

### Recovering Lost Manifests

If a manifest is lost or corrupted:

```bash
# Option 1: Recreate from package (if you still have it)
deploy-tool pack ./models --auto --type model --version 1.0.1 --force

# Option 2: Restore from Git history
git checkout <commit-hash> -- deployment/manifests/model-1.0.1.manifest.json

# Option 3: Check other branches
git branch -a --contains deployment/manifests/model-1.0.1.manifest.json
```

### Manifest Version Conflicts

When the same version number is used by different people:

```bash
# Best practice: Increment version
deploy-tool pack ./models --auto --type model --version 1.0.2

# Alternative: Use branch suffix
deploy-tool pack ./models --auto --type model --version 1.0.1-feature-xyz

# For releases: Use unique identifiers
deploy-tool publish \
  --component model:1.0.1-alice \
  --release-version 2024.01.20-experiment
```

Remember: Git is your safety net. When in doubt, commit your manifests!