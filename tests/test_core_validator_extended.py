"""
Extended tests for NQESH Question Validator to increase coverage.

This test file specifically targets:
- Hidden file skipping logic
- File upload error handling
- Cache creation failure fallback
- Batch validation error handling
- Per-question validation
- Main function execution
"""
import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO
import sys

from src.nqesh_generator.core.validator import NQESHQuestionValidator, main
from src.nqesh_generator.models.question_models import Question, QuestionBank, Category
from src.nqesh_generator.models.validation_models import (
    ValidationReport, QuestionValidationResult, ValidationIssue, BatchValidationResult
)
from src.nqesh_generator import config


# ============================================================================
# FILE UPLOAD WITH HIDDEN FILES
# ============================================================================

@pytest.mark.integration
class TestValidatorHiddenFiles:
    """Test handling of hidden files during upload."""

    def test_upload_source_files_skips_hidden_files(self, mock_env_vars, temp_dir, capsys):
        """Test that hidden files are skipped during upload."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        # Create regular files
        (files_dir / "source1.txt").write_text("Source 1")
        (files_dir / "source2.pdf").write_text("Source 2")

        # Create hidden files (should be skipped)
        (files_dir / ".gitkeep").write_text("")
        (files_dir / ".DS_Store").write_text("Mac hidden file")

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            # Mock file upload
            mock_file = Mock()
            mock_file.name = "test_file"
            mock_file.uri = "https://example.com/file"
            mock_file.mime_type = "text/plain"
            mock_file.state = "ACTIVE"

            validator.client.files.upload = Mock(return_value=mock_file)
            validator.client.files.get = Mock(return_value=mock_file)

            # Upload files
            uploaded = validator.upload_source_files(str(files_dir))

            captured = capsys.readouterr()

            # Should skip hidden files
            assert "Skipping hidden file: .gitkeep" in captured.out
            assert "Skipping hidden file: .DS_Store" in captured.out

            # Should only upload 2 regular files
            assert len(uploaded) == 2


# ============================================================================
# FILE UPLOAD ERROR HANDLING
# ============================================================================

@pytest.mark.integration
class TestValidatorUploadErrors:
    """Test error handling during file upload."""

    def test_upload_files_individual_file_error(self, mock_env_vars, temp_dir, capsys):
        """Test that individual file upload errors don't stop the process."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        (files_dir / "good1.txt").write_text("Good 1")
        (files_dir / "bad.txt").write_text("Bad")
        (files_dir / "good2.txt").write_text("Good 2")

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            call_count = [0]
            def upload_side_effect(file):
                call_count[0] += 1
                if "bad" in str(file):
                    raise Exception("Upload failed")
                mock_file = Mock()
                mock_file.name = f"file_{call_count[0]}"
                mock_file.uri = f"https://example.com/file{call_count[0]}"
                mock_file.mime_type = "text/plain"
                mock_file.state = "ACTIVE"
                return mock_file

            validator.client.files.upload = Mock(side_effect=upload_side_effect)
            validator.client.files.get = Mock(side_effect=lambda name: Mock(state="ACTIVE"))

            uploaded = validator.upload_source_files(str(files_dir))

            captured = capsys.readouterr()

            # Should show error for bad file
            assert "Error uploading bad.txt" in captured.out
            assert "Skipping this file and continuing" in captured.out

            # Should still upload 2 good files
            assert len(uploaded) == 2

    def test_upload_files_verification_failure(self, mock_env_vars, temp_dir, capsys):
        """Test handling of file verification failures."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        (files_dir / "document.txt").write_text("Content")

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            mock_file = Mock()
            mock_file.name = "test_file"
            mock_file.uri = "https://example.com/file"
            mock_file.mime_type = "text/plain"

            validator.client.files.upload = Mock(return_value=mock_file)
            validator.client.files.get = Mock(side_effect=Exception("Verification failed"))

            uploaded = validator.upload_source_files(str(files_dir))

            captured = capsys.readouterr()

            assert "Warning: Could not verify file access" in captured.out
            assert len(uploaded) == 1


# ============================================================================
# CACHE CREATION FAILURE
# ============================================================================

@pytest.mark.integration
class TestValidatorCacheFailure:
    """Test handling of cache creation failures."""

    def test_create_cached_content_failure_fallback(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test graceful fallback when cache creation fails."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            validator.client.caches.create = Mock(
                side_effect=Exception("Cache creation failed")
            )

            result = validator.create_cached_content()

            captured = capsys.readouterr()

            assert "Warning: Could not create cache" in captured.out
            assert "Cache creation failed" in captured.out
            assert "Falling back to non-cached validation" in captured.out

            assert result is None
            assert validator.cached_content is None


# ============================================================================
# BATCH VALIDATION ERROR HANDLING
# ============================================================================

@pytest.mark.integration
class TestValidatorBatchErrors:
    """Test batch validation error handling."""

    def test_validate_question_bank_batch_error_creates_error_results(
        self, mock_env_vars, mock_uploaded_files, temp_dir, sample_questions, capsys
    ):
        """Test that batch validation errors create error results for all questions in batch."""
        # Create question bank file
        question_bank = QuestionBank(
            categories=[
                Category(id="cat1", name="Category 1", description="Desc 1")
            ],
            questions={
                "cat1": sample_questions
            }
        )

        question_bank_file = temp_dir / "questions.json"
        with open(question_bank_file, 'w') as f:
            json.dump(question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            # Mock cache creation
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            validator.client.caches.create = Mock(return_value=mock_cache)

            # Mock batch validation to fail
            validator.client.models.generate_content = Mock(
                side_effect=Exception("Batch API error")
            )

            # Validate - should handle error gracefully
            report = validator.validate_question_bank(
                question_bank_file=str(question_bank_file),
                use_batch=True
            )

            captured = capsys.readouterr()

            # Should show error in output
            assert "ERROR in batch" in captured.out

            # Should create error results for all questions
            assert report.total_questions == len(sample_questions)
            for result in report.question_results:
                assert not result.is_valid
                assert any("Batch validation failed" in issue.description for issue in result.issues)

    def test_validate_question_bank_with_batch_size(
        self, mock_env_vars, mock_uploaded_files, temp_dir, sample_questions
    ):
        """Test batch validation with custom batch size."""
        # Create more questions to test batching
        many_questions = []
        for i in range(15):
            q = Question(
                question_id=f"Q{i:03d}",
                question=f"Question {i}",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation=f"Explanation {i}",
                source="https://deped.gov.ph"
            )
            many_questions.append(q)

        question_bank = QuestionBank(
            categories=[Category(id="cat1", name="Category 1", description="Desc")],
            questions={"cat1": many_questions}
        )

        question_bank_file = temp_dir / "questions.json"
        with open(question_bank_file, 'w') as f:
            json.dump(question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            # Mock cache
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            validator.client.caches.create = Mock(return_value=mock_cache)

            # Mock batch validation results
            def mock_generate(model, contents, config):
                # Return results for all questions in batch
                results = []
                for q in many_questions[:5]:  # First batch
                    results.append(QuestionValidationResult(
                        question_id=q.question_id,
                        category_id="cat1",
                        is_valid=True,
                        is_factually_accurate=True,
                        is_answer_correct=True,
                        is_explanation_accurate=True,
                        are_options_valid=True,
                        issues=[],
                        confidence_score=0.9,
                        notes="Valid"
                    ))

                batch_result = BatchValidationResult(results=results)
                mock_response = Mock()
                mock_response.text = batch_result.model_dump_json()
                return mock_response

            validator.client.models.generate_content = Mock(side_effect=mock_generate)

            # Validate with custom batch size
            report = validator.validate_question_bank(
                question_bank_file=str(question_bank_file),
                use_batch=True,
                batch_size=5
            )

            # Should process in multiple batches (15 questions / 5 per batch = 3 batches)
            assert validator.client.models.generate_content.call_count == 3


# ============================================================================
# PER-QUESTION VALIDATION
# ============================================================================

@pytest.mark.integration
class TestValidatorPerQuestion:
    """Test per-question validation mode."""

    def test_validate_question_bank_per_question_mode(
        self, mock_env_vars, mock_uploaded_files, temp_dir, sample_questions
    ):
        """Test validation using per-question mode instead of batch."""
        question_bank = QuestionBank(
            categories=[Category(id="cat1", name="Category 1", description="Desc")],
            questions={"cat1": sample_questions[:2]}  # Use 2 questions
        )

        question_bank_file = temp_dir / "questions.json"
        with open(question_bank_file, 'w') as f:
            json.dump(question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            # Mock cache
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            validator.client.caches.create = Mock(return_value=mock_cache)

            # Mock per-question validation
            def mock_validate_single(question, category_name, category_id):
                return QuestionValidationResult(
                    question_id=question.question_id,
                    category_id=category_id,
                    is_valid=True,
                    is_factually_accurate=True,
                    is_answer_correct=True,
                    is_explanation_accurate=True,
                    are_options_valid=True,
                    issues=[],
                    confidence_score=0.85,
                    notes="Valid question"
                )

            validator.validate_single_question = Mock(side_effect=mock_validate_single)

            # Validate using per-question mode
            report = validator.validate_question_bank(
                question_bank_file=str(question_bank_file),
                use_batch=False
            )

            # Should call validate_single_question for each question
            assert validator.validate_single_question.call_count == 2
            assert report.total_questions == 2
            assert report.valid_questions == 2

    def test_validate_question_bank_per_question_with_error(
        self, mock_env_vars, mock_uploaded_files, temp_dir, sample_questions, capsys
    ):
        """Test per-question validation with individual question errors."""
        question_bank = QuestionBank(
            categories=[Category(id="cat1", name="Category 1", description="Desc")],
            questions={"cat1": sample_questions[:2]}
        )

        question_bank_file = temp_dir / "questions.json"
        with open(question_bank_file, 'w') as f:
            json.dump(question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            # Mock cache
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            validator.client.caches.create = Mock(return_value=mock_cache)

            # Mock validation - first succeeds, second fails
            call_count = [0]
            def mock_validate_single(question, category_name, category_id):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise Exception("Validation API error")
                return QuestionValidationResult(
                    question_id=question.question_id,
                    category_id=category_id,
                    is_valid=True,
                    is_factually_accurate=True,
                    is_answer_correct=True,
                    is_explanation_accurate=True,
                    are_options_valid=True,
                    issues=[],
                    confidence_score=0.9,
                    notes="Valid"
                )

            validator.validate_single_question = Mock(side_effect=mock_validate_single)

            # Validate
            report = validator.validate_question_bank(
                question_bank_file=str(question_bank_file),
                use_batch=False
            )

            captured = capsys.readouterr()

            # Should show error
            assert "ERROR validating" in captured.out

            # Should have results for both (second one as error result)
            assert report.total_questions == 2
            assert report.valid_questions == 1
            assert report.invalid_questions == 1


# ============================================================================
# MAIN FUNCTION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidatorMain:
    """Test the main() function execution."""

    def test_main_success(self, mock_env_vars, temp_dir, sample_question_bank, capsys, monkeypatch):
        """Test successful execution of main()."""
        monkeypatch.chdir(temp_dir)

        # Create files directory
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)
        (files_dir / "test.txt").write_text("Test")

        # Create question bank
        question_bank_file = temp_dir / "output" / "nqesh_questions.json"
        question_bank_file.parent.mkdir(exist_ok=True)
        with open(question_bank_file, 'w') as f:
            json.dump(sample_question_bank.model_dump(), f)

        with patch('src.nqesh_generator.core.validator.genai.Client'):
            with patch('src.nqesh_generator.core.validator.NQESHQuestionValidator') as MockVal:
                # Mock validator instance
                mock_val = Mock()
                mock_val.upload_source_files = Mock()

                # Create mock report
                mock_report = ValidationReport(
                    validation_timestamp="2025-01-01T00:00:00",
                    total_questions=10,
                    valid_questions=9,
                    invalid_questions=1,
                    category_summaries=[],
                    question_results=[],
                    overall_accuracy_rate=90.0,
                    overall_confidence=0.85,
                    critical_issues_count=0,
                    recommendations=["1 question needs review"]
                )

                mock_val.validate_question_bank = Mock(return_value=mock_report)
                mock_val.save_validation_report = Mock()
                mock_val.cleanup_files = Mock()

                MockVal.return_value = mock_val

                # Run main
                main()

                # Verify workflow
                mock_val.upload_source_files.assert_called_once()
                mock_val.validate_question_bank.assert_called_once()
                mock_val.save_validation_report.assert_called_once()
                mock_val.cleanup_files.assert_called_once()

                captured = capsys.readouterr()
                assert "NQESH QUESTION BANK VALIDATOR" in captured.out
                assert "VALIDATION SUMMARY" in captured.out
                assert "Validation completed with context caching" in captured.out

    def test_main_no_api_key(self, clean_env, capsys):
        """Test main() when API key is not set."""
        with patch('src.nqesh_generator.core.validator.load_env'):
            with patch.dict(os.environ, {}, clear=True):
                main()

                captured = capsys.readouterr()
                assert "ERROR: GEMINI_API_KEY environment variable not set" in captured.out

    def test_main_exception_handling(self, mock_env_vars, capsys):
        """Test main() handling of exceptions."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            with patch('src.nqesh_generator.core.validator.NQESHQuestionValidator') as MockVal:
                MockVal.side_effect = Exception("Validation error")

                main()

                captured = capsys.readouterr()
                assert "ERROR: Validation error" in captured.out


# ============================================================================
# CLEANUP WITH CACHE
# ============================================================================

@pytest.mark.integration
class TestValidatorCleanupWithCache:
    """Test cleanup including cache deletion."""

    def test_cleanup_files_deletes_cache(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test that cleanup deletes the cache."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            mock_cache = Mock()
            mock_cache.name = "validator_cache_123"
            validator.cached_content = mock_cache

            validator.client.caches.delete = Mock()
            validator.client.files.delete = Mock()

            validator.cleanup_files()

            validator.client.caches.delete.assert_called_once_with(name="validator_cache_123")

            captured = capsys.readouterr()
            assert "Deleted cache: validator_cache_123" in captured.out

    def test_cleanup_files_cache_deletion_error(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test handling of cache deletion errors."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()
            validator.uploaded_files = mock_uploaded_files

            mock_cache = Mock()
            mock_cache.name = "test_cache"
            validator.cached_content = mock_cache

            validator.client.caches.delete = Mock(side_effect=Exception("Delete failed"))
            validator.client.files.delete = Mock()

            validator.cleanup_files()

            captured = capsys.readouterr()
            assert "Error deleting cache" in captured.out


# ============================================================================
# MARKDOWN REPORT EDGE CASES
# ============================================================================

@pytest.mark.integration
class TestValidatorMarkdownReportEdgeCases:
    """Test edge cases in markdown report generation."""

    def test_markdown_report_with_notes(self, mock_env_vars):
        """Test markdown report includes notes field."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            # Create report with notes
            result_with_notes = QuestionValidationResult(
                question_id="Q001",
                category_id="cat1",
                is_valid=True,
                is_factually_accurate=True,
                is_answer_correct=True,
                is_explanation_accurate=True,
                are_options_valid=True,
                issues=[],
                confidence_score=0.95,
                notes="This is a well-crafted question with excellent clarity."
            )

            report = ValidationReport(
                validation_timestamp="2025-01-01T00:00:00",
                total_questions=1,
                valid_questions=1,
                invalid_questions=0,
                category_summaries=[],
                question_results=[result_with_notes],
                overall_accuracy_rate=100.0,
                overall_confidence=0.95,
                critical_issues_count=0,
                recommendations=[]
            )

            markdown = validator._generate_markdown_report(report)

            # Should include notes
            assert "Notes: This is a well-crafted question" in markdown

    def test_markdown_report_without_notes(self, mock_env_vars):
        """Test markdown report handles missing notes gracefully."""
        with patch('src.nqesh_generator.core.validator.genai.Client'):
            validator = NQESHQuestionValidator()

            result_no_notes = QuestionValidationResult(
                question_id="Q001",
                category_id="cat1",
                is_valid=True,
                is_factually_accurate=True,
                is_answer_correct=True,
                is_explanation_accurate=True,
                are_options_valid=True,
                issues=[],
                confidence_score=0.95,
                notes=""  # Empty notes
            )

            report = ValidationReport(
                validation_timestamp="2025-01-01T00:00:00",
                total_questions=1,
                valid_questions=1,
                invalid_questions=0,
                category_summaries=[],
                question_results=[result_no_notes],
                overall_accuracy_rate=100.0,
                overall_confidence=0.95,
                critical_issues_count=0,
                recommendations=[]
            )

            markdown = validator._generate_markdown_report(report)

            # Should not crash with empty notes
            assert "Q001" in markdown
