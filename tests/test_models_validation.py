"""
Unit tests for validation models (validation_models.py).

Tests cover:
- ValidationIssue model
- QuestionValidationResult model
- CategoryValidationSummary model
- ValidationReport model
- Field constraints and validation
"""
import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.nqesh_generator.models.validation_models import (
    ValidationIssue,
    QuestionValidationResult,
    CategoryValidationSummary,
    ValidationReport
)


# ============================================================================
# VALIDATION ISSUE TESTS
# ============================================================================

@pytest.mark.unit
class TestValidationIssue:
    """Test ValidationIssue model."""

    def test_validation_issue_creation_valid(self, sample_validation_issue):
        """Test creating a valid validation issue."""
        assert sample_validation_issue.severity == "major"
        assert sample_validation_issue.issue_type == "factual_error"
        assert "contradicts" in sample_validation_issue.description
        assert sample_validation_issue.evidence is not None
        assert sample_validation_issue.suggestion is not None

    def test_validation_issue_minimal(self):
        """Test validation issue with minimal required fields."""
        issue = ValidationIssue(
            severity="minor",
            issue_type="option_issues",
            description="Options are too similar"
        )

        assert issue.severity == "minor"
        assert issue.issue_type == "option_issues"
        assert issue.evidence is None
        assert issue.suggestion is None

    def test_validation_issue_severity_constraint(self):
        """Test that severity must be one of: critical, major, minor."""
        # Valid severities
        for severity in ["critical", "major", "minor"]:
            issue = ValidationIssue(
                severity=severity,
                issue_type="factual_error",
                description="Test"
            )
            assert issue.severity == severity

        # Invalid severity
        with pytest.raises(ValidationError) as exc_info:
            ValidationIssue(
                severity="invalid",
                issue_type="factual_error",
                description="Test"
            )

        assert "severity" in str(exc_info.value)

    def test_validation_issue_type_constraint(self):
        """Test that issue_type must be one of the allowed values."""
        valid_types = [
            "factual_error",
            "answer_mismatch",
            "explanation_incorrect",
            "source_not_found",
            "option_issues",
            "validation_error"
        ]

        for issue_type in valid_types:
            issue = ValidationIssue(
                severity="minor",
                issue_type=issue_type,
                description="Test"
            )
            assert issue.issue_type == issue_type

        # Invalid type
        with pytest.raises(ValidationError):
            ValidationIssue(
                severity="minor",
                issue_type="invalid_type",
                description="Test"
            )

    def test_validation_issue_serialization(self, sample_validation_issue):
        """Test validation issue serialization."""
        data = sample_validation_issue.model_dump()

        assert data["severity"] == sample_validation_issue.severity
        assert data["issue_type"] == sample_validation_issue.issue_type
        assert data["description"] == sample_validation_issue.description
        assert data["evidence"] == sample_validation_issue.evidence
        assert data["suggestion"] == sample_validation_issue.suggestion

    def test_validation_issue_json_round_trip(self, sample_validation_issue):
        """Test JSON serialization and deserialization."""
        json_str = sample_validation_issue.model_dump_json()
        restored = ValidationIssue.model_validate_json(json_str)

        assert restored.severity == sample_validation_issue.severity
        assert restored.issue_type == sample_validation_issue.issue_type
        assert restored.description == sample_validation_issue.description


# ============================================================================
# QUESTION VALIDATION RESULT TESTS
# ============================================================================

@pytest.mark.unit
class TestQuestionValidationResult:
    """Test QuestionValidationResult model."""

    def test_validation_result_valid_question(self, sample_validation_result):
        """Test validation result for a valid question."""
        assert sample_validation_result.is_valid is True
        assert sample_validation_result.is_factually_accurate is True
        assert sample_validation_result.is_answer_correct is True
        assert sample_validation_result.is_explanation_accurate is True
        assert sample_validation_result.are_options_valid is True
        assert len(sample_validation_result.issues) == 0
        assert sample_validation_result.confidence_score == 0.95

    def test_validation_result_invalid_question(self, sample_validation_result_with_issues):
        """Test validation result for an invalid question."""
        result = sample_validation_result_with_issues

        assert result.is_valid is False
        assert result.is_factually_accurate is False
        assert len(result.issues) > 0
        assert result.confidence_score < 1.0

    def test_validation_result_confidence_score_range(self):
        """Test that confidence score must be between 0.0 and 1.0."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            result = QuestionValidationResult(
                question_id="Q001",
                category_id="test",
                is_valid=True,
                is_factually_accurate=True,
                is_answer_correct=True,
                is_explanation_accurate=True,
                are_options_valid=True,
                confidence_score=score
            )
            assert result.confidence_score == score

        # Invalid scores
        for invalid_score in [-0.1, 1.1, 2.0]:
            with pytest.raises(ValidationError):
                QuestionValidationResult(
                    question_id="Q001",
                    category_id="test",
                    is_valid=True,
                    is_factually_accurate=True,
                    is_answer_correct=True,
                    is_explanation_accurate=True,
                    are_options_valid=True,
                    confidence_score=invalid_score
                )

    def test_validation_result_empty_issues(self):
        """Test validation result with no issues."""
        result = QuestionValidationResult(
            question_id="Q001",
            category_id="test",
            is_valid=True,
            is_factually_accurate=True,
            is_answer_correct=True,
            is_explanation_accurate=True,
            are_options_valid=True,
            confidence_score=1.0,
            issues=[]
        )

        assert len(result.issues) == 0
        assert result.is_valid is True

    def test_validation_result_multiple_issues(self):
        """Test validation result with multiple issues."""
        issues = [
            ValidationIssue(
                severity="critical",
                issue_type="factual_error",
                description="Factual error found"
            ),
            ValidationIssue(
                severity="major",
                issue_type="answer_mismatch",
                description="Answer is incorrect"
            ),
            ValidationIssue(
                severity="minor",
                issue_type="option_issues",
                description="Options are ambiguous"
            )
        ]

        result = QuestionValidationResult(
            question_id="Q001",
            category_id="test",
            is_valid=False,
            is_factually_accurate=False,
            is_answer_correct=False,
            is_explanation_accurate=True,
            are_options_valid=False,
            confidence_score=0.5,
            issues=issues
        )

        assert len(result.issues) == 3
        assert result.issues[0].severity == "critical"
        assert result.issues[1].severity == "major"
        assert result.issues[2].severity == "minor"

    def test_validation_result_serialization(self, sample_validation_result):
        """Test validation result serialization."""
        data = sample_validation_result.model_dump()

        assert data["question_id"] == sample_validation_result.question_id
        assert data["category_id"] == sample_validation_result.category_id
        assert data["is_valid"] == sample_validation_result.is_valid
        assert data["confidence_score"] == sample_validation_result.confidence_score

    def test_validation_result_json_round_trip(self, sample_validation_result):
        """Test JSON round trip."""
        json_str = sample_validation_result.model_dump_json()
        restored = QuestionValidationResult.model_validate_json(json_str)

        assert restored.question_id == sample_validation_result.question_id
        assert restored.is_valid == sample_validation_result.is_valid
        assert restored.confidence_score == sample_validation_result.confidence_score


# ============================================================================
# CATEGORY VALIDATION SUMMARY TESTS
# ============================================================================

@pytest.mark.unit
class TestCategoryValidationSummary:
    """Test CategoryValidationSummary model."""

    def test_category_summary_creation(self, sample_category_validation_summary):
        """Test creating a category validation summary."""
        summary = sample_category_validation_summary

        assert summary.category_id == "educational-leadership"
        assert summary.category_name == "Educational Leadership"
        assert summary.total_questions == 10
        assert summary.valid_questions == 8
        assert summary.invalid_questions == 2
        assert summary.average_confidence == 0.87

    def test_category_summary_all_valid(self):
        """Test summary where all questions are valid."""
        summary = CategoryValidationSummary(
            category_id="test",
            category_name="Test Category",
            total_questions=5,
            valid_questions=5,
            invalid_questions=0,
            critical_issues=0,
            major_issues=0,
            minor_issues=0,
            average_confidence=1.0
        )

        assert summary.valid_questions == summary.total_questions
        assert summary.invalid_questions == 0
        assert summary.critical_issues == 0

    def test_category_summary_all_invalid(self):
        """Test summary where all questions are invalid."""
        summary = CategoryValidationSummary(
            category_id="test",
            category_name="Test Category",
            total_questions=5,
            valid_questions=0,
            invalid_questions=5,
            critical_issues=3,
            major_issues=2,
            minor_issues=1,
            average_confidence=0.3
        )

        assert summary.valid_questions == 0
        assert summary.invalid_questions == summary.total_questions

    def test_category_summary_confidence_range(self):
        """Test that average confidence must be between 0.0 and 1.0."""
        # Valid
        for conf in [0.0, 0.5, 1.0]:
            summary = CategoryValidationSummary(
                category_id="test",
                category_name="Test",
                total_questions=5,
                valid_questions=5,
                invalid_questions=0,
                critical_issues=0,
                major_issues=0,
                minor_issues=0,
                average_confidence=conf
            )
            assert summary.average_confidence == conf

        # Invalid
        for invalid_conf in [-0.1, 1.1]:
            with pytest.raises(ValidationError):
                CategoryValidationSummary(
                    category_id="test",
                    category_name="Test",
                    total_questions=5,
                    valid_questions=5,
                    invalid_questions=0,
                    critical_issues=0,
                    major_issues=0,
                    minor_issues=0,
                    average_confidence=invalid_conf
                )

    def test_category_summary_serialization(self, sample_category_validation_summary):
        """Test category summary serialization."""
        data = sample_category_validation_summary.model_dump()

        assert data["category_id"] == sample_category_validation_summary.category_id
        assert data["total_questions"] == sample_category_validation_summary.total_questions
        assert data["valid_questions"] == sample_category_validation_summary.valid_questions


# ============================================================================
# VALIDATION REPORT TESTS
# ============================================================================

@pytest.mark.unit
class TestValidationReport:
    """Test ValidationReport model."""

    def test_validation_report_creation(self, sample_validation_report):
        """Test creating a validation report."""
        report = sample_validation_report

        assert report.total_questions == 10
        assert report.valid_questions == 8
        assert report.invalid_questions == 2
        assert report.overall_accuracy_rate == 80.0
        assert report.overall_confidence == 0.87
        assert len(report.category_summaries) > 0
        assert len(report.question_results) > 0

    def test_validation_report_empty(self):
        """Test creating an empty validation report."""
        report = ValidationReport(
            validation_timestamp=datetime.now().isoformat(),
            total_questions=0,
            valid_questions=0,
            invalid_questions=0,
            category_summaries=[],
            question_results=[],
            overall_accuracy_rate=0.0,
            overall_confidence=0.0,
            critical_issues_count=0,
            recommendations=[]
        )

        assert report.total_questions == 0
        assert len(report.category_summaries) == 0
        assert len(report.question_results) == 0

    def test_validation_report_accuracy_rate_range(self):
        """Test that accuracy rate must be between 0.0 and 100.0."""
        # Valid rates
        for rate in [0.0, 50.0, 100.0]:
            report = ValidationReport(
                validation_timestamp=datetime.now().isoformat(),
                total_questions=10,
                valid_questions=5,
                invalid_questions=5,
                category_summaries=[],
                question_results=[],
                overall_accuracy_rate=rate,
                overall_confidence=0.5,
                critical_issues_count=0
            )
            assert report.overall_accuracy_rate == rate

        # Invalid rates
        for invalid_rate in [-1.0, 101.0]:
            with pytest.raises(ValidationError):
                ValidationReport(
                    validation_timestamp=datetime.now().isoformat(),
                    total_questions=10,
                    valid_questions=5,
                    invalid_questions=5,
                    category_summaries=[],
                    question_results=[],
                    overall_accuracy_rate=invalid_rate,
                    overall_confidence=0.5,
                    critical_issues_count=0
                )

    def test_validation_report_with_recommendations(self):
        """Test validation report with recommendations."""
        recommendations = [
            "Review questions with critical issues",
            "Improve source documentation",
            "Validate explanations"
        ]

        report = ValidationReport(
            validation_timestamp=datetime.now().isoformat(),
            total_questions=10,
            valid_questions=7,
            invalid_questions=3,
            category_summaries=[],
            question_results=[],
            overall_accuracy_rate=70.0,
            overall_confidence=0.75,
            critical_issues_count=2,
            recommendations=recommendations
        )

        assert len(report.recommendations) == 3
        assert report.recommendations[0] == recommendations[0]

    def test_validation_report_serialization(self, sample_validation_report):
        """Test validation report serialization."""
        data = sample_validation_report.model_dump()

        assert isinstance(data, dict)
        assert data["total_questions"] == sample_validation_report.total_questions
        assert data["valid_questions"] == sample_validation_report.valid_questions
        assert isinstance(data["category_summaries"], list)
        assert isinstance(data["question_results"], list)

    def test_validation_report_json_round_trip(self, sample_validation_report):
        """Test validation report JSON round trip."""
        json_str = sample_validation_report.model_dump_json()
        restored = ValidationReport.model_validate_json(json_str)

        assert restored.total_questions == sample_validation_report.total_questions
        assert restored.valid_questions == sample_validation_report.valid_questions
        assert restored.overall_accuracy_rate == sample_validation_report.overall_accuracy_rate

    def test_validation_report_file_save_load(self, sample_validation_report, temp_dir):
        """Test saving and loading validation report from file."""
        file_path = temp_dir / "validation_report.json"

        # Save
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_validation_report.model_dump(), f, indent=2)

        # Load
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        restored = ValidationReport.model_validate(data)

        assert restored.total_questions == sample_validation_report.total_questions
        assert restored.overall_accuracy_rate == sample_validation_report.overall_accuracy_rate

    def test_validation_report_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        timestamp = datetime.now().isoformat()

        report = ValidationReport(
            validation_timestamp=timestamp,
            total_questions=10,
            valid_questions=8,
            invalid_questions=2,
            category_summaries=[],
            question_results=[],
            overall_accuracy_rate=80.0,
            overall_confidence=0.9,
            critical_issues_count=0
        )

        assert report.validation_timestamp == timestamp
        # Verify it's a valid ISO format string
        assert "T" in report.validation_timestamp or " " in report.validation_timestamp
