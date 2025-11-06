"""
Integration tests for NQESH Question Validator (validator.py).

Tests cover:
- Validator initialization
- File upload functionality
- Cached content creation
- Single question validation
- Question bank validation
- Report generation and saving
- Error handling
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.nqesh_generator.core.validator import NQESHQuestionValidator
from src.nqesh_generator.models.validation_models import (
    ValidationReport, QuestionValidationResult
)
from src.nqesh_generator import config


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorInitialization:
    """Test validator initialization."""

    def test_init_with_api_key(self, mock_env_vars):
        """Test initializing validator with API key."""
        with patch('src.nqesh_generator.core.validator.genai.Client') as mock_client:
            validator = NQESHQuestionValidator(api_key="test-key")

            mock_client.assert_called_once_with(api_key="test-key")
            assert validator.model_name == config.VALIDATOR_MODEL_NAME
            assert validator.uploaded_files == []
            assert validator.cached_content is None

    def test_init_without_api_key(self, mock_env_vars):
        """Test initializing validator without explicit API key."""
        with patch('src.nqesh_generator.core.validator.genai.Client') as mock_client:
            validator = NQESHQuestionValidator()

            mock_client.assert_called_once()
            assert validator.model_name == config.VALIDATOR_MODEL_NAME

    def test_init_custom_model_name(self, mock_env_vars):
        """Test initializing with custom model name."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator(model_name="custom-validator-model")

            assert validator.model_name == "custom-validator-model"


# ============================================================================
# FILE UPLOAD TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorFileUpload:
    """Test file upload functionality."""

    def test_upload_source_files_success(self, mock_env_vars, mock_files_dir, mock_uploaded_files):
        """Test successful source file upload."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            validator.client.files.upload = Mock(side_effect=mock_uploaded_files)
            validator.client.files.get = Mock(side_effect=mock_uploaded_files)

            uploaded = validator.upload_source_files(str(mock_files_dir))

            assert len(uploaded) == 2
            assert validator.client.files.upload.call_count == 2

    def test_upload_source_files_directory_not_found(self, mock_env_vars):
        """Test upload when directory doesn't exist."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            with pytest.raises(FileNotFoundError) as exc_info:
                validator.upload_source_files("nonexistent_directory")

            assert "not found" in str(exc_info.value)

    def test_upload_source_files_empty_directory(self, mock_env_vars, temp_dir):
        """Test upload when directory is empty."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            with pytest.raises(FileNotFoundError) as exc_info:
                validator.upload_source_files(str(empty_dir))

            assert "No files found" in str(exc_info.value)


# ============================================================================
# CACHED CONTENT TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorCachedContent:
    """Test cached content creation for validation."""

    def test_create_cached_content_success(self, mock_env_vars, mock_uploaded_files):
        """Test creating cached content successfully."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            cached = validator.create_cached_content()

            assert cached is not None
            assert "files" in cached
            assert "base_instruction" in cached
            assert "contents" in cached
            assert len(cached["files"]) == len(mock_uploaded_files)

    def test_create_cached_content_no_files(self, mock_env_vars):
        """Test creating cached content without uploaded files."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            with pytest.raises(ValueError) as exc_info:
                validator.create_cached_content()

            assert "No source files uploaded" in str(exc_info.value)

    def test_cached_content_structure(self, mock_env_vars, mock_uploaded_files):
        """Test the structure of cached content."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            cached = validator.create_cached_content()

            # Verify structure
            assert isinstance(cached["contents"], list)
            # Should have files + base instruction
            assert len(cached["contents"]) == len(mock_uploaded_files) + 1


# ============================================================================
# SINGLE QUESTION VALIDATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorSingleQuestion:
    """Test single question validation."""

    def test_validate_single_question_success(
        self, mock_env_vars, mock_uploaded_files, sample_question, mock_validation_response
    ):
        """Test successfully validating a single question."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files
            validator.cached_content = {
                "files": mock_uploaded_files,
                "base_instruction": "Test instruction",
                "contents": []
            }

            validator.client.models.generate_content = Mock(return_value=mock_validation_response)

            result = validator.validate_single_question(
                question=sample_question,
                category_name="Test Category",
                category_id="test-category"
            )

            assert isinstance(result, QuestionValidationResult)
            assert result.question_id == sample_question.question_id
            validator.client.models.generate_content.assert_called_once()

    def test_validate_single_question_no_files(self, mock_env_vars, sample_question):
        """Test validation without uploaded files."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            with pytest.raises(ValueError) as exc_info:
                validator.validate_single_question(
                    sample_question, "Category", "cat-id"
                )

            assert "No source files uploaded" in str(exc_info.value)

    def test_validate_single_question_no_cache(
        self, mock_env_vars, mock_uploaded_files, sample_question
    ):
        """Test validation without cached content."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            with pytest.raises(ValueError) as exc_info:
                validator.validate_single_question(
                    sample_question, "Category", "cat-id"
                )

            assert "Cached content not created" in str(exc_info.value)


# ============================================================================
# QUESTION BANK VALIDATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorQuestionBank:
    """Test question bank validation."""

    def test_validate_question_bank_success(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank_json,
        mock_validation_response
    ):
        """Test successfully validating a question bank."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            validator.client.models.generate_content = Mock(return_value=mock_validation_response)

            report = validator.validate_question_bank(str(sample_question_bank_json))

            assert isinstance(report, ValidationReport)
            assert report.total_questions > 0
            assert len(report.question_results) > 0

    def test_validate_question_bank_file_not_found(self, mock_env_vars):
        """Test validation when question bank file doesn't exist."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            with pytest.raises(FileNotFoundError):
                validator.validate_question_bank("nonexistent_file.json")

    def test_validate_question_bank_default_path(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank,
        mock_validation_response, temp_dir, monkeypatch
    ):
        """Test validation with default question bank path."""
        monkeypatch.chdir(temp_dir)

        # Create default output file
        output_dir = temp_dir / config.OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)
        default_file = output_dir / config.QUESTIONS_OUTPUT_FILE

        with open(default_file, 'w', encoding='utf-8') as f:
            json.dump(sample_question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            validator.client.models.generate_content = Mock(return_value=mock_validation_response)

            report = validator.validate_question_bank()

            assert isinstance(report, ValidationReport)


# ============================================================================
# VALIDATION REPORT GENERATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorReportGeneration:
    """Test validation report generation."""

    def test_generate_validation_report(
        self, mock_env_vars, sample_question_bank, sample_validation_result
    ):
        """Test generating validation report from results."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            # Create list of results
            results = [sample_validation_result] * 10

            report = validator._generate_validation_report(sample_question_bank, results)

            assert isinstance(report, ValidationReport)
            assert report.total_questions == 10
            assert len(report.question_results) == 10
            assert len(report.category_summaries) > 0

    def test_report_accuracy_calculation(
        self, mock_env_vars, sample_question_bank, sample_validation_result
    ):
        """Test accuracy rate calculation in report."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            # 8 valid, 2 invalid
            valid_result = sample_validation_result
            invalid_result = QuestionValidationResult(
                question_id="Q001",
                category_id="test",
                is_valid=False,
                is_factually_accurate=False,
                is_answer_correct=False,
                is_explanation_accurate=False,
                are_options_valid=False,
                confidence_score=0.3
            )

            results = [valid_result] * 8 + [invalid_result] * 2

            report = validator._generate_validation_report(sample_question_bank, results)

            assert report.total_questions == 10
            assert report.valid_questions == 8
            assert report.invalid_questions == 2
            assert report.overall_accuracy_rate == 80.0

    def test_report_recommendations(
        self, mock_env_vars, sample_question_bank, sample_validation_result
    ):
        """Test recommendation generation in report."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            # Create results with issues
            invalid_result = QuestionValidationResult(
                question_id="Q001",
                category_id="test",
                is_valid=False,
                is_factually_accurate=False,
                is_answer_correct=False,
                is_explanation_accurate=False,
                are_options_valid=False,
                confidence_score=0.5
            )

            results = [invalid_result] * 10

            report = validator._generate_validation_report(sample_question_bank, results)

            assert len(report.recommendations) > 0
            assert report.overall_accuracy_rate < 90


# ============================================================================
# REPORT SAVING TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorReportSaving:
    """Test saving validation reports."""

    def test_save_validation_report_json(
        self, mock_env_vars, sample_validation_report, temp_dir
    ):
        """Test saving validation report as JSON."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            json_output = temp_dir / "validation.json"
            md_output = temp_dir / "validation.md"

            validator.save_validation_report(
                sample_validation_report,
                str(json_output),
                str(md_output)
            )

            # Verify JSON file
            assert json_output.exists()
            with open(json_output, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert "total_questions" in data
            assert "validation_timestamp" in data

    def test_save_validation_report_markdown(
        self, mock_env_vars, sample_validation_report, temp_dir
    ):
        """Test saving validation report as Markdown."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            json_output = temp_dir / "validation.json"
            md_output = temp_dir / "validation.md"

            validator.save_validation_report(
                sample_validation_report,
                str(json_output),
                str(md_output)
            )

            # Verify Markdown file
            assert md_output.exists()
            content = md_output.read_text()
            assert "# NQESH Question Bank Validation Report" in content
            assert "## Summary" in content

    def test_save_validation_report_default_paths(
        self, mock_env_vars, sample_validation_report, temp_dir, monkeypatch
    ):
        """Test saving with default output paths."""
        monkeypatch.chdir(temp_dir)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            validator.save_validation_report(sample_validation_report)

            # Check default files exist
            json_file = Path(config.OUTPUT_DIR) / config.VALIDATION_REPORT_JSON
            md_file = Path(config.OUTPUT_DIR) / config.VALIDATION_REPORT_MD

            assert json_file.exists()
            assert md_file.exists()


# ============================================================================
# MARKDOWN REPORT GENERATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorMarkdownReport:
    """Test markdown report generation."""

    def test_generate_markdown_report(self, mock_env_vars, sample_validation_report):
        """Test generating markdown report."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            markdown = validator._generate_markdown_report(sample_validation_report)

            assert "# NQESH Question Bank Validation Report" in markdown
            assert "## Summary" in markdown
            assert "## Category Summaries" in markdown
            assert "## Question Details" in markdown

    def test_markdown_report_with_issues(
        self, mock_env_vars, sample_validation_result_with_issues
    ):
        """Test markdown report includes issue details."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            report = ValidationReport(
                validation_timestamp=datetime.now().isoformat(),
                total_questions=1,
                valid_questions=0,
                invalid_questions=1,
                category_summaries=[],
                question_results=[sample_validation_result_with_issues],
                overall_accuracy_rate=0.0,
                overall_confidence=0.65,
                critical_issues_count=0
            )

            markdown = validator._generate_markdown_report(report)

            assert "INVALID" in markdown
            assert "Issues:" in markdown

    def test_markdown_report_with_recommendations(self, mock_env_vars):
        """Test markdown report includes recommendations."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            report = ValidationReport(
                validation_timestamp=datetime.now().isoformat(),
                total_questions=10,
                valid_questions=7,
                invalid_questions=3,
                category_summaries=[],
                question_results=[],
                overall_accuracy_rate=70.0,
                overall_confidence=0.75,
                critical_issues_count=1,
                recommendations=[
                    "Review critical issues",
                    "Improve accuracy"
                ]
            )

            markdown = validator._generate_markdown_report(report)

            assert "## Recommendations" in markdown
            assert "Review critical issues" in markdown


# ============================================================================
# FILE CLEANUP TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorCleanup:
    """Test file cleanup operations."""

    def test_cleanup_files(self, mock_env_vars, mock_uploaded_files):
        """Test cleanup of uploaded files."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files
            validator.cached_content = {"test": "data"}

            validator.client.files.delete = Mock()

            validator.cleanup_files()

            # Should delete all uploaded files
            assert validator.client.files.delete.call_count == len(mock_uploaded_files)
            assert len(validator.uploaded_files) == 0
            assert validator.cached_content is None

    def test_cleanup_files_with_errors(self, mock_env_vars, mock_uploaded_files):
        """Test cleanup when deletion fails."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            validator.client.files.delete = Mock(side_effect=Exception("Delete failed"))

            # Should not raise exception
            validator.cleanup_files()

            assert len(validator.uploaded_files) == 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorErrorHandling:
    """Test error handling in validator."""

    def test_api_error_during_validation(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank_json
    ):
        """Test handling of API errors during validation."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            validator.client.models.generate_content = Mock(
                side_effect=Exception("API Error")
            )

            # Should handle error gracefully and include in report
            report = validator.validate_question_bank(str(sample_question_bank_json))

            assert isinstance(report, ValidationReport)
            # All results should be marked as failed
            assert all(not r.is_valid for r in report.question_results)

    def test_invalid_json_response(
        self, mock_env_vars, mock_uploaded_files, sample_question, sample_question_bank_json
    ):
        """Test handling of invalid JSON in API response."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            # Mock invalid JSON response
            mock_response = Mock()
            mock_response.text = "invalid json"
            validator.client.models.generate_content = Mock(return_value=mock_response)

            # Should handle error in validation report
            report = validator.validate_question_bank(str(sample_question_bank_json))

            assert isinstance(report, ValidationReport)
