# NQESH Question Generator - Test Suite

## Overview

This directory contains comprehensive tests for the NQESH Question Generator application. The test suite follows Python testing best practices and achieves **85% code coverage**.

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures and pytest configuration
├── test_models_question.py      # Unit tests for question models
├── test_models_validation.py    # Unit tests for validation models
├── test_utils_env_loader.py     # Unit tests for environment loader
├── test_core_generator.py       # Integration tests for question generator
├── test_core_validator.py       # Integration tests for question validator
└── test_imports.py             # Import verification tests
```

## Test Categories

### Unit Tests (@pytest.mark.unit)
- **Models**: Test Pydantic model validation, serialization, and constraints
- **Utilities**: Test environment variable loading and file operations
- Focus on isolated, fast-running tests

### Integration Tests (@pytest.mark.integration)
- **Generator**: Test question generation workflow with mocked API
- **Validator**: Test validation workflow with mocked API
- Test interactions between components

## Running Tests

### Run All Tests
```bash
source venv/bin/activate
pytest tests/
```

### Run Specific Test Categories
```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run specific test file
pytest tests/test_models_question.py

# Run specific test class
pytest tests/test_models_question.py::TestCategory

# Run specific test
pytest tests/test_models_question.py::TestCategory::test_category_creation_valid
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=src/nqesh_generator --cov-report=term-missing
```

### Run with HTML Coverage Report
```bash
pytest tests/ --cov=src/nqesh_generator --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Coverage

Current coverage: **85%**

| Module | Coverage |
|--------|----------|
| models/question_models.py | 100% |
| models/validation_models.py | 100% |
| utils/env_loader.py | 100% |
| config.py | 100% |
| core/generator.py | 80% |
| core/validator.py | 84% |

### Uncovered Code
- Main functions in `generator.py` and `validator.py` (lines 394-461)
- Error handling in production code paths

## Key Fixtures

### Model Fixtures (conftest.py)
- `sample_category` - Single Category instance
- `sample_categories` - List of Category instances
- `sample_question` - Single Question instance
- `sample_questions` - List of Question instances
- `sample_question_bank` - Complete QuestionBank instance
- `sample_validation_result` - ValidationResult instance
- `sample_validation_report` - ValidationReport instance

### Mock Fixtures
- `mock_genai_client` - Mocked Google GenAI client
- `mock_uploaded_file` - Mocked uploaded file object
- `mock_uploaded_files` - List of mocked uploaded files
- `mock_generate_response` - Mocked API response for generation
- `mock_validation_response` - Mocked API response for validation

### Environment Fixtures
- `mock_env_vars` - Sets test environment variables
- `clean_env` - Removes API key from environment
- `temp_dir` - Temporary directory for file operations
- `mock_files_dir` - Mock files directory with test files

## Writing New Tests

### Follow the AAA Pattern
```python
def test_example():
    # Arrange - Set up test data
    data = {"key": "value"}

    # Act - Perform the action
    result = function_under_test(data)

    # Assert - Verify the outcome
    assert result == expected_value
```

### Use Descriptive Test Names
```python
# Good
def test_category_creation_with_valid_data():
    ...

# Bad
def test_category():
    ...
```

### Use Fixtures for Reusable Setup
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

### Test Edge Cases
- Empty inputs
- Missing required fields
- Invalid data types
- Boundary conditions
- Error scenarios

## Best Practices Implemented

1. **DRY (Don't Repeat Yourself)**: Shared fixtures in `conftest.py`
2. **Isolation**: Each test is independent and can run in any order
3. **Mocking**: External dependencies (API calls) are mocked
4. **Markers**: Tests are categorized with pytest markers
5. **Coverage**: Comprehensive test coverage with reports
6. **Assertions**: Clear, specific assertions
7. **Documentation**: Docstrings explain what each test does
8. **Organization**: Tests organized by module and functionality

## Test Markers

```python
@pytest.mark.unit        # Fast, isolated unit tests
@pytest.mark.integration # Tests with component interaction
@pytest.mark.slow        # Tests that take longer to run
@pytest.mark.api         # Tests requiring API access
```

## Continuous Integration

The test suite is configured for CI/CD:
- Runs on every commit
- Enforces 80% minimum coverage
- Fast execution (< 1 second for full suite)
- Clear failure reporting

## Troubleshooting

### Tests Fail Due to Missing Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Tests Fail Due to Import Errors
Ensure you're running from project root:
```bash
cd /path/to/questions-generator
pytest tests/
```

### Coverage Not Generated
Install coverage dependencies:
```bash
pip install pytest-cov coverage
```

## Adding New Tests

When adding new functionality:

1. Write tests first (TDD approach)
2. Add fixtures to `conftest.py` if reusable
3. Use appropriate markers (`@pytest.mark.unit` or `@pytest.mark.integration`)
4. Ensure tests are isolated and don't depend on external state
5. Mock external dependencies (API calls, file system when appropriate)
6. Document complex test scenarios with docstrings
7. Run tests locally before committing
8. Verify coverage doesn't drop below 80%

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/validation/)
