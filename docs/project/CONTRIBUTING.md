# Contributing to AI Hedge Fund

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Style](#code-style)
4. [Testing](#testing)
5. [Pull Request Process](#pull-request-process)
6. [Adding New Features](#adding-new-features)
7. [Reporting Bugs](#reporting-bugs)

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- TA-Lib system library
- Git

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-hedge-fund.git
cd ai-hedge-fund

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/ai-hedge-fund.git
```

## Development Setup

### Backend

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black ruff mypy

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/

# Start dev server
make run
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Run linter
npm run lint

# Build for production
npm run build
```

## Code Style

### Python

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy . --exclude venv --exclude frontend
```

**Style Guidelines:**
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Use descriptive variable names
- Maximum line length: 100 characters (Black default)

**Example:**
```python
def analyze_stock(
    symbol: str,
    include_narrative: bool = True
) -> Dict[str, Any]:
    """
    Analyze a stock and return comprehensive scoring.

    Args:
        symbol: Stock symbol (e.g., "TCS")
        include_narrative: Whether to generate LLM narrative

    Returns:
        Dictionary with score, recommendation, agent scores, etc.
    """
    # Implementation
```

### TypeScript/React

We use:
- **ESLint** for linting
- **TypeScript strict mode**
- **Prettier** (via Vite)

```bash
cd frontend

# Lint
npm run lint

# Type check
npm run type-check
```

**Style Guidelines:**
- Use TypeScript interfaces for all props
- Use functional components with hooks
- Keep components small (< 200 lines)
- Use meaningful component names
- Extract reusable logic into custom hooks

**Example:**
```typescript
interface StockCardProps {
  analysis: StockAnalysis;
  detailed?: boolean;
}

export default function StockCard({ analysis, detailed = false }: StockCardProps) {
  // Implementation
}
```

## Testing

### Writing Tests

Tests are required for all new features and bug fixes.

**Backend:**
```python
# tests/test_my_feature.py
import pytest

@pytest.mark.unit
class TestMyFeature:
    """Tests for MyFeature"""

    def test_basic_functionality(self, sample_data):
        """Test basic functionality"""
        result = my_function(sample_data)
        assert result is not None
        assert result['key'] == 'expected_value'
```

**Running Tests:**
```bash
# All tests
pytest tests/

# Specific markers
pytest tests/ -m unit
pytest tests/ -m integration

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

- Aim for >80% overall coverage
- >90% for critical components (agents, stock scorer)
- All public APIs must be tested
- Edge cases and error handling must be tested

## Pull Request Process

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-new-feature
# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following style guidelines
- Add tests for new functionality
- Update documentation if needed
- Run tests locally
- Format code

```bash
# Format and lint
make format
make lint

# Run tests
make test

# Check all
make test && make lint && make format-check
```

### 3. Commit Changes

Use conventional commits:

```bash
git commit -m "feat: add new momentum indicator"
git commit -m "fix: correct P/E calculation for negative earnings"
git commit -m "docs: update API documentation"
git commit -m "test: add tests for fundamentals agent"
git commit -m "refactor: simplify data provider logic"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create pull request on GitHub
# Fill out the PR template with:
# - Description of changes
# - Related issues
# - Testing performed
# - Screenshots (if UI changes)
```

### 5. PR Review Process

- Automated tests must pass
- Code review by maintainers
- Address feedback
- Squash commits if needed
- Merge when approved

## Adding New Features

### Adding a New Agent

1. Create agent file in `agents/`:

```python
# agents/new_agent.py
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class NewAgent:
    """
    New Agent for analyzing XYZ

    Scoring: 0-100 with confidence
    """

    def __init__(self):
        self.agent_name = "NewAgent"
        self.weight = 0.15  # 15%

    def analyze(self, symbol: str, cached_data: Optional[Dict]) -> Dict:
        """Analyze stock for XYZ metrics"""
        # Implementation
        return {
            'score': 75.0,
            'confidence': 0.8,
            'reasoning': 'Summary of analysis',
            'metrics': {},
            'breakdown': {},
            'agent': self.agent_name
        }
```

2. Add to Stock Scorer:

```python
# core/stock_scorer.py
from agents.new_agent import NewAgent

class StockScorer:
    STATIC_WEIGHTS = {
        'fundamentals': 0.30,
        'momentum': 0.25,
        # ... other agents
        'new_agent': 0.15,  # Add new agent
    }

    def __init__(self):
        self.agents = {
            # ... existing agents
            'new_agent': NewAgent(),
        }
```

3. Add tests:

```python
# tests/test_agents.py
@pytest.mark.unit
@pytest.mark.agents
class TestNewAgent:
    def test_initialization(self):
        agent = NewAgent()
        assert agent.agent_name == "NewAgent"
        assert agent.weight == 0.15

    def test_analyze(self, sample_data):
        agent = NewAgent()
        result = agent.analyze('TCS', sample_data)
        assert 0 <= result['score'] <= 100
```

4. Update documentation:
- Add to README.md
- Add to ARCHITECTURE.md
- Update API documentation

### Adding a New API Endpoint

1. Add Pydantic models:

```python
# api/main.py
class NewRequest(BaseModel):
    parameter: str = Field(..., description="Parameter description")

class NewResponse(BaseModel):
    result: str
```

2. Add endpoint:

```python
@app.post("/new-endpoint", response_model=NewResponse, tags=["Category"])
async def new_endpoint(request: NewRequest):
    """
    Endpoint description

    Returns XYZ data
    """
    try:
        # Implementation
        return NewResponse(result="success")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

3. Add tests:

```python
# tests/test_api.py
def test_new_endpoint(api_client):
    response = api_client.post(
        '/new-endpoint',
        json={'parameter': 'value'}
    )
    assert response.status_code == 200
```

4. Update frontend to use new endpoint

### Adding a New Index

1. Add data to `data/nifty_constituents.py`:

```python
NIFTY_NEWINDEX = {
    'SYMBOL1': {
        'name': 'Company Name',
        'sector': 'Sector',
        'industry': 'Industry',
        'market_cap': 'Large Cap',
        'weight': 10.5
    },
    # ... more stocks
}
```

2. Add to `get_all_indices()`:

```python
def get_all_indices():
    return {
        'NIFTY_50': NIFTY_50,
        'NIFTY_NEWINDEX': NIFTY_NEWINDEX,
        # ... others
    }
```

3. Test with stock universe explorer:

```bash
python scripts/explore_universe.py summary NIFTY_NEWINDEX
```

## Reporting Bugs

### Before Reporting

- Check if issue already exists
- Verify it's not a configuration issue
- Test with latest version
- Reproduce the bug consistently

### Bug Report Template

```markdown
**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- Backend version: [e.g., 1.0.0]

**Logs:**
```
Paste relevant logs here
```

**Screenshots:**
If applicable
```

## Feature Requests

### Feature Request Template

```markdown
**Feature Description:**
Clear description of the feature

**Use Case:**
Why is this feature needed?

**Proposed Solution:**
How would you implement it?

**Alternatives:**
Other approaches considered

**Additional Context:**
Any other information
```

## Code Review Guidelines

### For Contributors

- Be responsive to feedback
- Ask questions if unclear
- Keep PRs focused and small
- Update based on review comments

### For Reviewers

- Be respectful and constructive
- Focus on code quality and maintainability
- Test the changes locally
- Approve when standards are met

## Documentation

When adding features, update:

- [ ] Code docstrings
- [ ] README.md (if user-facing)
- [ ] ARCHITECTURE.md (if architectural change)
- [ ] API documentation (if new endpoint)
- [ ] Test documentation

## Community

- Be respectful and inclusive
- Help others learn
- Share knowledge
- Give credit where due
- Follow the code of conduct

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Questions?

If you have questions:
1. Check existing documentation
2. Search closed issues
3. Ask in discussions
4. Contact maintainers

Thank you for contributing! 🚀
