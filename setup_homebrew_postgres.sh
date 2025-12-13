#!/bin/bash
# Setup script for Homebrew and PostgreSQL

set -e

echo "🔧 Setting up Homebrew and PostgreSQL..."
echo ""

# Step 1: Add Homebrew to PATH
echo "📝 Step 1: Adding Homebrew to PATH..."
if [ -f /opt/homebrew/bin/brew ]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo "✅ Homebrew added to PATH"
else
    echo "❌ Homebrew not found at /opt/homebrew/bin/brew"
    exit 1
fi

# Step 2: Verify Homebrew
echo ""
echo "📝 Step 2: Verifying Homebrew installation..."
brew --version
echo "✅ Homebrew is working"

# Step 3: Install PostgreSQL
echo ""
echo "📝 Step 3: Installing PostgreSQL (this may take a few minutes)..."
brew install postgresql
echo "✅ PostgreSQL installed"

# Step 4: Verify PostgreSQL
echo ""
echo "📝 Step 4: Verifying PostgreSQL installation..."
psql --version
echo "✅ PostgreSQL is ready"

echo ""
echo "🎉 Setup complete! You can now use 'psql' to connect to your database."
echo ""
echo "To connect to your database, run:"
echo 'psql "postgresql://postgres:<PASSWORD>@health-app-db.c5c224qc6drg.eu-north-1.rds.amazonaws.com:5432/health_app"'

