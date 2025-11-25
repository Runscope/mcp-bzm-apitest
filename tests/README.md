# Unit Tests for MCP BlazeMeter API Test Server

This directory contains comprehensive unit tests for the MCP BlazeMeter API Test server.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_models.py           # Tests for BaseResult and data models
├── test_token.py            # Tests for token configuration
├── test_api_client.py       # Tests for API client functionality
├── test_test_manager.py     # Tests for TestManager
├── test_bucket_manager.py   # Tests for BucketManager
├── test_step_manager.py     # Tests for StepManager
├── test_schedule_manager.py # Tests for ScheduleManager
├── test_result_manager.py   # Tests for ResultManager
└── test_integration.py      # Integration tests
```

## Running Tests

### Install Test Dependencies

```bash
# Using pip
pip install -e ".[test]"

# Or install directly
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestBaseResult

# Run specific test method
pytest tests/test_models.py::TestBaseResult::test_base_result_creation_with_success
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only async tests
pytest -m asyncio
```

## Test Coverage

The test suite covers:

1. **Models** (`test_models.py`)
   - BaseResult model creation and methods
   - Model serialization (JSON)
   - Warning, info, and hint handling

2. **Token Management** (`test_token.py`)
   - Token validation
   - Token creation with various inputs
   - Error handling for invalid tokens

3. **API Client** (`test_api_client.py`)
   - HTTP request handling
   - Authentication headers
   - Error responses (401, 403)
   - Result formatting
   - Pagination

4. **Managers** (Various `test_*_manager.py` files)
   - CRUD operations for each resource type
   - Error handling
   - API integration
   - Parameter validation

5. **Integration Tests** (`test_integration.py`)
   - Tool registration
   - End-to-end workflows
   - Multi-manager interactions

## Writing New Tests

### Example Unit Test

```python
import pytest
from src.models import BaseResult

class TestNewFeature:
    """Test cases for new feature"""

    def test_feature_basic(self):
        """Test basic functionality"""
        result = BaseResult(result=[{"id": "1"}])
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_feature_async(self, mock_token, mock_context):
        """Test async functionality"""
        # Your async test code here
        pass
```

### Using Fixtures

Common fixtures available in `conftest.py`:
- `mock_token` - Mock BlazeMeter API token
- `mock_context` - Mock MCP context
- `sample_*_data` - Sample data for various resources
- `mock_httpx_response` - Mock HTTP responses
- `mock_api_request` - Mock API request function

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   - `test_read_bucket` instead of `test_read`
   - `test_create_schedule_with_invalid_interval` instead of `test_error`

2. **Arrange-Act-Assert Pattern**:
   ```python
   def test_example(self):
       # Arrange - set up test data
       manager = TestManager(token, ctx)
       
       # Act - perform the action
       result = await manager.read("bucket", "test")
       
       # Assert - verify the results
       assert result.error is None
   ```

3. **Mock External Dependencies**: Always mock API calls and external services

4. **Test Edge Cases**: Include tests for:
   - Empty inputs
   - Invalid inputs
   - Error conditions
   - Boundary values

5. **Async Tests**: Mark async tests with `@pytest.mark.asyncio`

## Continuous Integration

Tests should be run automatically on:
- Every pull request
- Before merging to main branch
- Scheduled daily runs

## Coverage Goals

Target coverage: **>80%** for all modules

Current coverage can be checked by running:
```bash
pytest --cov=src --cov-report=term-missing
```

## Troubleshooting

### Common Issues

1. **ImportError**: Make sure you've installed the package in development mode:
   ```bash
   pip install -e .
   ```

2. **Async test errors**: Ensure `pytest-asyncio` is installed:
   ```bash
   pip install pytest-asyncio
   ```

3. **Coverage not working**: Install `pytest-cov`:
   ```bash
   pip install pytest-cov
   ```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

