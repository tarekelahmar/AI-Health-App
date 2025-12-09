# GitHub Actions Workflows

This directory contains CI/CD workflows for the Health App.

## Workflows

### 1. CI (`ci.yml`)
**Triggers:** Push/PR to `main` or `develop` branches

**Jobs:**
- **test**: Runs pytest tests with PostgreSQL service
- **lint**: Checks code formatting and linting

**Requirements:**
- Set `OPENAI_API_KEY` in GitHub Secrets (optional for tests)

### 2. CD (`cd.yml`)
**Triggers:** Push to `main` branch or manual dispatch

**Jobs:**
- **build-and-push**: Builds and tests Docker image
- **deploy**: Deployment steps (customize for your infrastructure)

### 3. Docker Build (`docker-build.yml`)
**Triggers:** Push to `main`, tags, or PRs

**Features:**
- Builds Docker image
- Pushes to Docker Hub (if credentials provided)
- Tags images with version, branch, and SHA
- Uses GitHub Actions cache for faster builds

**Requirements:**
- Set `DOCKER_USERNAME` and `DOCKER_PASSWORD` in GitHub Secrets (optional)

## Setting up GitHub Secrets

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `OPENAI_API_KEY`: Your OpenAI API key (for tests)
   - `DOCKER_USERNAME`: Docker Hub username (optional)
   - `DOCKER_PASSWORD`: Docker Hub password/token (optional)

## Workflow Status

View workflow runs at: `https://github.com/[USERNAME]/[REPO]/actions`

