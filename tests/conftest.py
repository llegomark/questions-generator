"""
Pytest configuration and shared fixtures for NQESH Question Generator tests.

This module provides reusable fixtures and test utilities following
pytest best practices for maintainable and DRY test code.
"""
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock

import pytest

from src.nqesh_generator.models.question_models import (
    Category, Question, QuestionBank
)
from src.nqesh_generator.models.validation_models import (
    ValidationIssue, QuestionValidationResult, CategoryValidationSummary,
    ValidationReport
)


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "api: Tests requiring API access")


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_api_key = "test-gemini-api-key-12345"
    monkeypatch.setenv("GEMINI_API_KEY", test_api_key)
    return {"GEMINI_API_KEY": test_api_key}


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment with no API key set."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


# ============================================================================
# FILE SYSTEM FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_files_dir(temp_dir):
    """Create a mock files directory with test files."""
    files_dir = temp_dir / "files"
    files_dir.mkdir(exist_ok=True)

    # Create mock DepEd Order files
    (files_dir / "deped_order_001.txt").write_text(
        "DepEd Order No. 001: Test educational policy content."
    )
    (files_dir / "deped_order_002.txt").write_text(
        "DepEd Order No. 002: Test curriculum standards."
    )

    return files_dir


@pytest.fixture
def mock_env_file(temp_dir):
    """Create a mock .env file."""
    env_file = temp_dir / ".env"
    env_file.write_text("GEMINI_API_KEY=test-key-from-file\n")
    return env_file


# ============================================================================
# MODEL FIXTURES - Category
# ============================================================================

@pytest.fixture
def sample_category() -> Category:
    """Create a sample Category instance."""
    return Category(
        id="educational-leadership",
        name="Educational Leadership",
        description="Questions on leadership theories and school management"
    )


@pytest.fixture
def sample_categories() -> List[Category]:
    """Create a list of sample categories."""
    return [
        Category(
            id="educational-leadership",
            name="Educational Leadership",
            description="Leadership theories and school management"
        ),
        Category(
            id="curriculum-instruction",
            name="Curriculum and Instruction",
            description="Curriculum development and instructional strategies"
        ),
        Category(
            id="legal-ethical",
            name="Legal and Ethical Foundations",
            description="Education laws, policies, and ethical standards"
        )
    ]


# ============================================================================
# MODEL FIXTURES - Question
# ============================================================================

@pytest.fixture
def sample_question() -> Question:
    """Create a sample Question instance."""
    return Question(
        question_id="EL001",
        question="What is the primary role of a school head?",
        options=[
            "To teach classes",
            "To provide instructional leadership",
            "To maintain the building",
            "To handle finances only"
        ],
        correct_answer="To provide instructional leadership",
        explanation="According to DepEd Order, the school head's primary role is instructional leadership.",
        source="https://deped.gov.ph"
    )


@pytest.fixture
def sample_questions() -> List[Question]:
    """Create a list of sample questions."""
    return [
        Question(
            question_id="EL001",
            question="What is the primary role of a school head?",
            options=[
                "To teach classes",
                "To provide instructional leadership",
                "To maintain the building",
                "To handle finances only"
            ],
            correct_answer="To provide instructional leadership",
            explanation="The school head's primary role is instructional leadership.",
            source="https://deped.gov.ph"
        ),
        Question(
            question_id="EL002",
            question="Which leadership style is most effective?",
            options=[
                "Autocratic",
                "Transformational",
                "Laissez-faire",
                "Transactional"
            ],
            correct_answer="Transformational",
            explanation="Transformational leadership is most effective for school improvement.",
            source="https://deped.gov.ph"
        )
    ]


# ============================================================================
# MODEL FIXTURES - QuestionBank
# ============================================================================

@pytest.fixture
def sample_question_bank(sample_categories, sample_questions) -> QuestionBank:
    """Create a sample QuestionBank instance."""
    return QuestionBank(
        categories=sample_categories[:2],  # Use first 2 categories
        questions={
            "educational-leadership": sample_questions,
            "curriculum-instruction": [sample_questions[0]]
        }
    )


@pytest.fixture
def sample_question_bank_json(sample_question_bank, temp_dir) -> Path:
    """Create a sample question bank JSON file."""
    json_file = temp_dir / "test_questions.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sample_question_bank.model_dump(), f, indent=2)
    return json_file


# ============================================================================
# VALIDATION MODEL FIXTURES
# ============================================================================

@pytest.fixture
def sample_validation_issue() -> ValidationIssue:
    """Create a sample ValidationIssue."""
    return ValidationIssue(
        severity="major",
        issue_type="factual_error",
        description="The stated fact contradicts source document",
        evidence="Source states X, but question states Y",
        suggestion="Revise the question to align with source material"
    )


@pytest.fixture
def sample_validation_result() -> QuestionValidationResult:
    """Create a sample QuestionValidationResult."""
    return QuestionValidationResult(
        question_id="EL001",
        category_id="educational-leadership",
        is_valid=True,
        is_factually_accurate=True,
        is_answer_correct=True,
        is_explanation_accurate=True,
        are_options_valid=True,
        issues=[],
        confidence_score=0.95,
        notes="Question is well-formed and accurate"
    )


@pytest.fixture
def sample_validation_result_with_issues(sample_validation_issue) -> QuestionValidationResult:
    """Create a sample QuestionValidationResult with issues."""
    return QuestionValidationResult(
        question_id="EL002",
        category_id="educational-leadership",
        is_valid=False,
        is_factually_accurate=False,
        is_answer_correct=True,
        is_explanation_accurate=False,
        are_options_valid=True,
        issues=[sample_validation_issue],
        confidence_score=0.65,
        notes="Contains factual inaccuracies"
    )


@pytest.fixture
def sample_category_validation_summary() -> CategoryValidationSummary:
    """Create a sample CategoryValidationSummary."""
    return CategoryValidationSummary(
        category_id="educational-leadership",
        category_name="Educational Leadership",
        total_questions=10,
        valid_questions=8,
        invalid_questions=2,
        critical_issues=0,
        major_issues=2,
        minor_issues=1,
        average_confidence=0.87
    )


@pytest.fixture
def sample_validation_report(
    sample_validation_result,
    sample_category_validation_summary
) -> ValidationReport:
    """Create a sample ValidationReport."""
    return ValidationReport(
        validation_timestamp="2025-01-15T10:30:00",
        total_questions=10,
        valid_questions=8,
        invalid_questions=2,
        category_summaries=[sample_category_validation_summary],
        question_results=[sample_validation_result] * 10,
        overall_accuracy_rate=80.0,
        overall_confidence=0.87,
        critical_issues_count=0,
        recommendations=[
            "2 question(s) require review and correction",
            "2 major issues need attention"
        ]
    )


# ============================================================================
# MOCK GOOGLE AI API FIXTURES
# ============================================================================

@pytest.fixture
def mock_genai_client():
    """Create a mock Google GenAI client."""
    client = MagicMock()

    # Mock files API
    client.files = MagicMock()
    client.files.upload = MagicMock()
    client.files.get = MagicMock()
    client.files.delete = MagicMock()

    # Mock models API
    client.models = MagicMock()
    client.models.generate_content = MagicMock()

    return client


@pytest.fixture
def mock_uploaded_file():
    """Create a mock uploaded file object."""
    mock_file = Mock()
    mock_file.name = "files/test_file.txt"
    mock_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test123"
    mock_file.mime_type = "text/plain"
    mock_file.state = "ACTIVE"
    return mock_file


@pytest.fixture
def mock_uploaded_files(mock_uploaded_file):
    """Create a list of mock uploaded files."""
    file1 = Mock()
    file1.name = "files/deped_order_001.txt"
    file1.uri = "https://generativelanguage.googleapis.com/v1beta/files/file1"
    file1.mime_type = "text/plain"
    file1.state = "ACTIVE"

    file2 = Mock()
    file2.name = "files/deped_order_002.txt"
    file2.uri = "https://generativelanguage.googleapis.com/v1beta/files/file2"
    file2.mime_type = "text/plain"
    file2.state = "ACTIVE"

    return [file1, file2]


@pytest.fixture
def mock_generate_response(sample_question_bank):
    """Create a mock API response for question generation."""
    mock_response = Mock()
    mock_response.text = sample_question_bank.model_dump_json()
    return mock_response


@pytest.fixture
def mock_validation_response(sample_validation_result):
    """Create a mock API response for validation."""
    mock_response = Mock()
    mock_response.text = sample_validation_result.model_dump_json()
    return mock_response


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def capture_stdout():
    """Capture stdout for testing print statements."""
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    yield sys.stdout

    sys.stdout = old_stdout


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment after each test."""
    yield
    # Cleanup happens here after test completes
