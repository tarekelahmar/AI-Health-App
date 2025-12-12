#!/bin/bash
# Pre-commit hook to check for model changes without migrations
# This script can be added to .git/hooks/pre-commit

echo "Checking for model changes without migrations..."

# Check if any model files were modified
MODEL_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "app/domain/models/.*\.py$")

if [ -n "$MODEL_FILES" ]; then
    echo "⚠️  Model files modified:"
    echo "$MODEL_FILES"
    echo ""
    echo "❌ ERROR: Model changes detected without a migration!"
    echo ""
    echo "Please create a migration first:"
    echo "  make migrate-create MESSAGE=\"your change description\""
    echo ""
    echo "Or if this is intentional (e.g., only docstring changes),"
    echo "skip this check with: git commit --no-verify"
    exit 1
fi

echo "✅ No model changes detected. Proceeding with commit."
exit 0

