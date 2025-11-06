"""
Extended tests for NQESH Question Generator to increase coverage.

This test file specifically targets:
- Hidden file skipping logic
- File upload error handling
- Cache creation failure fallback
- Token usage display
- Main function execution
"""
import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO
import sys

from src.nqesh_generator.core.generator import NQESHQuestionGenerator, main
from src.nqesh_generator.models.question_models import QuestionBank
from src.nqesh_generator import config


# ============================================================================
# FILE UPLOAD WITH HIDDEN FILES
# ============================================================================

@pytest.mark.integration
class TestGeneratorHiddenFiles:
    """Test handling of hidden files during upload."""

    def test_upload_files_skips_hidden_files(self, mock_env_vars, temp_dir, capsys):
        """Test that hidden files are skipped during upload."""
        # Create files directory with hidden files
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        # Create regular files
        (files_dir / "document1.txt").write_text("Regular file 1")
        (files_dir / "document2.pdf").write_text("Regular file 2")

        # Create hidden files (should be skipped)
        (files_dir / ".gitkeep").write_text("")
        (files_dir / ".hidden").write_text("Hidden content")

        with patch('src.nqesh_generator.core.generator.genai.Client') as mock_client:
            generator = NQESHQuestionGenerator()

            # Mock file upload
            mock_file = Mock()
            mock_file.name = "test_file"
            mock_file.uri = "https://example.com/file"
            mock_file.mime_type = "text/plain"
            mock_file.state = "ACTIVE"

            generator.client.files.upload = Mock(return_value=mock_file)
            generator.client.files.get = Mock(return_value=mock_file)

            # Upload files
            uploaded = generator.upload_files(str(files_dir))

            # Capture output
            captured = capsys.readouterr()

            # Should skip hidden files
            assert "Skipping hidden file: .gitkeep" in captured.out
            assert "Skipping hidden file: .hidden" in captured.out

            # Should only upload 2 regular files
            assert len(uploaded) == 2
            assert generator.client.files.upload.call_count == 2

    def test_upload_files_only_hidden_files(self, mock_env_vars, temp_dir):
        """Test uploading directory with only hidden files."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        # Create only hidden files
        (files_dir / ".gitkeep").write_text("")
        (files_dir / ".hidden").write_text("Hidden")

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            # This should succeed with 0 files
            uploaded = generator.upload_files(str(files_dir))

            # Should have no files uploaded
            assert len(uploaded) == 0


# ============================================================================
# FILE UPLOAD ERROR HANDLING
# ============================================================================

@pytest.mark.integration
class TestGeneratorUploadErrors:
    """Test error handling during file upload."""

    def test_upload_files_individual_file_error(self, mock_env_vars, temp_dir, capsys):
        """Test that individual file upload errors don't stop the entire process."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        (files_dir / "good_file.txt").write_text("Good content")
        (files_dir / "bad_file.txt").write_text("Bad content")
        (files_dir / "another_good.txt").write_text("Another good")

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            # Mock file upload - fail for bad_file.txt
            call_count = [0]
            def upload_side_effect(file):
                call_count[0] += 1
                if "bad_file" in str(file):
                    raise Exception("Upload failed for this file")
                mock_file = Mock()
                mock_file.name = f"file_{call_count[0]}"
                mock_file.uri = f"https://example.com/file{call_count[0]}"
                mock_file.mime_type = "text/plain"
                mock_file.state = "ACTIVE"
                return mock_file

            generator.client.files.upload = Mock(side_effect=upload_side_effect)
            generator.client.files.get = Mock(side_effect=lambda name: Mock(state="ACTIVE"))

            # Upload files
            uploaded = generator.upload_files(str(files_dir))

            # Capture output
            captured = capsys.readouterr()

            # Should show error for bad file
            assert "Error uploading bad_file.txt" in captured.out
            assert "Skipping this file and continuing" in captured.out

            # Should still upload the 2 good files
            assert len(uploaded) == 2

    def test_upload_files_verification_failure(self, mock_env_vars, temp_dir, capsys):
        """Test handling of file verification failures."""
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)

        (files_dir / "document.txt").write_text("Content")

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            # Mock successful upload but failed verification
            mock_file = Mock()
            mock_file.name = "test_file"
            mock_file.uri = "https://example.com/file"
            mock_file.mime_type = "text/plain"

            generator.client.files.upload = Mock(return_value=mock_file)
            generator.client.files.get = Mock(side_effect=Exception("Verification failed"))

            # Upload should succeed despite verification warning
            uploaded = generator.upload_files(str(files_dir))

            captured = capsys.readouterr()

            # Should show warning about verification
            assert "Warning: Could not verify file access" in captured.out
            assert "Verification failed" in captured.out

            # File should still be added to uploaded list
            assert len(uploaded) == 1


# ============================================================================
# CACHE CREATION FAILURE
# ============================================================================

@pytest.mark.integration
class TestGeneratorCacheFailure:
    """Test handling of cache creation failures."""

    def test_create_cached_content_failure_fallback(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test graceful fallback when cache creation fails."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock cache creation failure
            generator.client.caches.create = Mock(
                side_effect=Exception("Cache creation failed")
            )

            # Should not raise exception, but return None and show warning
            result = generator.create_cached_content()

            captured = capsys.readouterr()

            # Should show warning
            assert "Warning: Could not create cache" in captured.out
            assert "Cache creation failed" in captured.out
            assert "Falling back to non-cached generation" in captured.out

            # Should return None and set cached_content to None
            assert result is None
            assert generator.cached_content is None

    def test_generate_questions_without_cache_after_failure(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank
    ):
        """Test that generation works even after cache creation fails."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.cached_content = None  # Simulate failed cache creation

            # Mock successful generation
            mock_response = Mock()
            mock_response.text = sample_question_bank.model_dump_json()
            generator.client.models.generate_content = Mock(return_value=mock_response)

            # Should work without cache
            result = generator.generate_questions(use_cache=False)

            assert result is not None
            assert len(result.categories) > 0


# ============================================================================
# TOKEN USAGE DISPLAY
# ============================================================================

@pytest.mark.integration
class TestGeneratorTokenUsage:
    """Test token usage display for cached generation."""

    def test_generate_questions_displays_token_usage(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank, capsys
    ):
        """Test that token usage is displayed when using cache."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Create mock cached content
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            generator.cached_content = mock_cache

            # Mock response with usage metadata
            mock_response = Mock()
            mock_response.text = sample_question_bank.model_dump_json()

            # Add usage metadata
            usage_metadata = Mock()
            usage_metadata.cached_content_token_count = 5000
            usage_metadata.prompt_token_count = 150
            usage_metadata.candidates_token_count = 800
            mock_response.usage_metadata = usage_metadata

            generator.client.models.generate_content = Mock(return_value=mock_response)

            # Generate with cache
            result = generator.generate_questions(use_cache=True)

            captured = capsys.readouterr()

            # Should display token usage
            assert "Cached tokens used: 5000" in captured.out
            assert "New tokens processed: 150" in captured.out
            assert "Output tokens: 800" in captured.out

    def test_generate_questions_no_token_display_without_cache(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank, capsys
    ):
        """Test that token usage is not displayed when not using cache."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.cached_content = None

            # Mock response without usage metadata
            mock_response = Mock()
            mock_response.text = sample_question_bank.model_dump_json()
            # No usage_metadata attribute

            generator.client.models.generate_content = Mock(return_value=mock_response)

            # Generate without cache
            result = generator.generate_questions(use_cache=False)

            captured = capsys.readouterr()

            # Should not display token usage
            assert "Cached tokens used" not in captured.out


# ============================================================================
# MAIN FUNCTION TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorMain:
    """Test the main() function execution."""

    def test_main_success(self, mock_env_vars, temp_dir, sample_question_bank, capsys, monkeypatch):
        """Test successful execution of main()."""
        # Change to temp directory
        monkeypatch.chdir(temp_dir)

        # Create files directory
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)
        (files_dir / "test.txt").write_text("Test content")

        # Create output directory
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            with patch('src.nqesh_generator.core.generator.NQESHQuestionGenerator') as MockGen:
                # Mock generator instance
                mock_gen = Mock()
                mock_gen.upload_files = Mock()
                mock_gen.create_cached_content = Mock()
                mock_gen.generate_questions = Mock(return_value=sample_question_bank)
                mock_gen.display_summary = Mock()
                mock_gen.save_to_file = Mock()
                mock_gen.cleanup_files = Mock()

                MockGen.return_value = mock_gen

                # Run main
                main()

                # Verify workflow
                mock_gen.upload_files.assert_called_once()
                mock_gen.create_cached_content.assert_called_once()
                mock_gen.generate_questions.assert_called_once()
                mock_gen.display_summary.assert_called_once()
                mock_gen.save_to_file.assert_called_once()
                mock_gen.cleanup_files.assert_called_once()

                captured = capsys.readouterr()
                assert "NQESH TEST QUESTION GENERATOR" in captured.out
                assert "Process completed successfully" in captured.out

    def test_main_no_api_key(self, clean_env, capsys):
        """Test main() when API key is not set."""
        with patch('src.nqesh_generator.core.generator.load_env'):
            with patch.dict(os.environ, {}, clear=True):
                main()

                captured = capsys.readouterr()
                assert "ERROR: GEMINI_API_KEY environment variable not set" in captured.out

    def test_main_file_not_found(self, mock_env_vars, temp_dir, capsys, monkeypatch):
        """Test main() when files directory doesn't exist."""
        monkeypatch.chdir(temp_dir)

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            main()

            captured = capsys.readouterr()
            assert "ERROR" in captured.out
            assert "Please ensure:" in captured.out
            assert "Create a 'files' directory" in captured.out

    def test_main_general_exception(self, mock_env_vars, temp_dir, capsys, monkeypatch):
        """Test main() handling of general exceptions."""
        monkeypatch.chdir(temp_dir)

        # Create files directory to pass initial check
        files_dir = temp_dir / "files"
        files_dir.mkdir(exist_ok=True)
        (files_dir / "test.txt").write_text("Test")

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            with patch('src.nqesh_generator.core.generator.NQESHQuestionGenerator') as MockGen:
                # Make generator raise a general exception
                MockGen.side_effect = Exception("Something went wrong")

                main()

                captured = capsys.readouterr()
                assert "ERROR: Something went wrong" in captured.out


# ============================================================================
# CLEANUP WITH CACHE
# ============================================================================

@pytest.mark.integration
class TestGeneratorCleanupWithCache:
    """Test cleanup including cache deletion."""

    def test_cleanup_files_deletes_cache(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test that cleanup deletes the cache."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Set up cached content
            mock_cache = Mock()
            mock_cache.name = "test_cache_123"
            generator.cached_content = mock_cache

            generator.client.caches.delete = Mock()
            generator.client.files.delete = Mock()

            # Cleanup
            generator.cleanup_files()

            # Should delete cache
            generator.client.caches.delete.assert_called_once_with(name="test_cache_123")

            captured = capsys.readouterr()
            assert "Deleted cache: test_cache_123" in captured.out

    def test_cleanup_files_cache_deletion_error(self, mock_env_vars, mock_uploaded_files, capsys):
        """Test handling of cache deletion errors."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            mock_cache = Mock()
            mock_cache.name = "test_cache"
            generator.cached_content = mock_cache

            # Mock cache deletion error
            generator.client.caches.delete = Mock(side_effect=Exception("Cache delete failed"))
            generator.client.files.delete = Mock()

            # Should not raise exception
            generator.cleanup_files()

            captured = capsys.readouterr()
            assert "Error deleting cache" in captured.out
            assert "Cache delete failed" in captured.out


# ============================================================================
# CATEGORY GENERATION EDGE CASES
# ============================================================================

@pytest.mark.integration
class TestGeneratorCategoryEdgeCases:
    """Test edge cases in category-based generation."""

    def test_generate_by_category_uses_cache(
        self, mock_env_vars, mock_uploaded_files, sample_question_bank, capsys
    ):
        """Test that category generation uses cache."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock cache creation
            mock_cache = Mock()
            mock_cache.name = "test_cache"
            generator.client.caches.create = Mock(return_value=mock_cache)

            # Mock generation
            mock_response = Mock()
            mock_response.text = sample_question_bank.model_dump_json()
            generator.client.models.generate_content = Mock(return_value=mock_response)

            # Generate by category
            category_prompts = {
                "leadership": "Generate leadership questions"
            }

            result = generator.generate_questions_by_category(category_prompts)

            # Should create cache
            generator.client.caches.create.assert_called_once()

            captured = capsys.readouterr()
            assert "GENERATING QUESTIONS BY CATEGORY" in captured.out
            assert "with cached context" in captured.out
