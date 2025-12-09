# Contributing Guide

## Development Setup

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. Set up environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your values
   ```

5. Run tests:
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Use Black for code formatting
- Follow PEP 8 guidelines
- Type hints encouraged
- Docstrings for all functions/classes

## Testing

- Write tests for all new features
- Maintain test coverage > 80%
- Run tests before committing

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Ensure all tests pass
5. Submit PR with description

## Commit Messages

Use clear, descriptive commit messages:
- `feat: Add wearable device integration`
- `fix: Resolve database connection issue`
- `docs: Update API documentation`

