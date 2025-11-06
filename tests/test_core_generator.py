"""
Integration tests for NQESH Question Generator (generator.py).

Tests cover:
- Generator initialization
- File upload functionality
- Cached content creation
- Question generation
- File cleanup
- Error handling
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

from src.nqesh_generator.core.generator import NQESHQuestionGenerator
from src.nqesh_generator.models.question_models import QuestionBank
from src.nqesh_generator import config


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorInitialization:
    """Test generator initialization."""

    def test_init_with_api_key(self, mock_env_vars):
        """Test initializing generator with API key."""
        with patch('src.nqesh_generator.core.generator.genai.Client') as mock_client:
            generator = NQESHQuestionGenerator(api_key="test-key")

            mock_client.assert_called_once_with(api_key="test-key")
            assert generator.model_name == config.MODEL_NAME
            assert generator.system_instruction == config.SYSTEM_INSTRUCTION
            assert generator.uploaded_files == []
            assert generator.cached_content is None

    def test_init_without_api_key(self, mock_env_vars):
        """Test initializing generator without explicit API key."""
        with patch('src.nqesh_generator.core.generator.genai.Client') as mock_client:
            generator = NQESHQuestionGenerator()

            mock_client.assert_called_once()
            assert generator.model_name == config.MODEL_NAME

    def test_init_custom_model_name(self, mock_env_vars):
        """Test initializing with custom model name."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator(model_name="custom-model")

            assert generator.model_name == "custom-model"

    def test_init_custom_system_instruction(self, mock_env_vars):
        """Test initializing with custom system instruction."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            custom_instruction = "Custom instruction for testing"
            generator = NQESHQuestionGenerator(system_instruction=custom_instruction)

            assert generator.system_instruction == custom_instruction

    def test_init_custom_num_questions(self, mock_env_vars):
        """Test initializing with custom default number of questions."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator(default_num_questions=20)

            assert generator.default_num_questions == 20


# ============================================================================
# FILE UPLOAD TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorFileUpload:
    """Test file upload functionality."""

    def test_upload_files_success(self, mock_env_vars, mock_files_dir, mock_uploaded_files):
        """Test successful file upload."""
        with patch('src.nqesh_generator.core.generator.genai.Client') as mock_client:
            generator = NQESHQuestionGenerator()

            # Mock file upload and get methods
            generator.client.files.upload = Mock(side_effect=mock_uploaded_files)
            generator.client.files.get = Mock(side_effect=mock_uploaded_files)

            # Upload files
            uploaded = generator.upload_files(str(mock_files_dir))

            assert len(uploaded) == 2
            assert generator.client.files.upload.call_count == 2

    def test_upload_files_directory_not_found(self, mock_env_vars):
        """Test upload when directory doesn't exist."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            with pytest.raises(FileNotFoundError) as exc_info:
                generator.upload_files("nonexistent_directory")

            assert "not found" in str(exc_info.value)

    def test_upload_files_empty_directory(self, mock_env_vars, temp_dir):
        """Test upload when directory is empty."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            with pytest.raises(FileNotFoundError) as exc_info:
                generator.upload_files(str(empty_dir))

            assert "No files found" in str(exc_info.value)

    def test_upload_files_verification_failure(self, mock_env_vars, mock_files_dir, mock_uploaded_file):
        """Test file upload when verification fails."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            generator.client.files.upload = Mock(return_value=mock_uploaded_file)
            generator.client.files.get = Mock(side_effect=Exception("Verification failed"))

            # Should still succeed but log warning
            uploaded = generator.upload_files(str(mock_files_dir))

            assert len(uploaded) == 2


# ============================================================================
# CACHED CONTENT TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorCachedContent:
    """Test cached content creation."""

    def test_create_cached_content_success(self, mock_env_vars, mock_uploaded_files):
        """Test creating cached content successfully with real Gemini caching API."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock the caches.create response
            mock_cache = Mock()
            mock_cache.name = "cachedContents/test123"
            mock_cache.expire_time = "2025-01-01T12:00:00Z"
            generator.client.caches.create = Mock(return_value=mock_cache)

            cached = generator.create_cached_content()

            assert cached is not None
            assert hasattr(cached, 'name')
            assert cached.name == "cachedContents/test123"
            assert generator.cached_content == cached
            generator.client.caches.create.assert_called_once()

    def test_create_cached_content_no_files(self, mock_env_vars):
        """Test creating cached content without uploaded files."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            with pytest.raises(ValueError) as exc_info:
                generator.create_cached_content()

            assert "No files uploaded" in str(exc_info.value)

    def test_cached_content_structure(self, mock_env_vars, mock_uploaded_files):
        """Test that cached content is a real Gemini cache object."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock the caches.create response
            mock_cache = Mock()
            mock_cache.name = "cachedContents/test456"
            mock_cache.expire_time = "2025-01-01T13:00:00Z"
            generator.client.caches.create = Mock(return_value=mock_cache)

            cached = generator.create_cached_content()

            # Verify it's a cache object with proper attributes
            assert hasattr(cached, 'name')
            assert hasattr(cached, 'expire_time')
            assert cached.name.startswith("cachedContents/")

            # Verify caches.create was called with proper config
            call_args = generator.client.caches.create.call_args
            assert call_args is not None


# ============================================================================
# QUESTION GENERATION TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorQuestionGeneration:
    """Test question generation functionality."""

    def test_generate_questions_success(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test successful question generation."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            question_bank = generator.generate_questions()

            assert isinstance(question_bank, QuestionBank)
            assert len(question_bank.categories) > 0
            generator.client.models.generate_content.assert_called_once()

    def test_generate_questions_no_files(self, mock_env_vars):
        """Test generation without uploaded files."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            with pytest.raises(ValueError) as exc_info:
                generator.generate_questions()

            assert "No files uploaded" in str(exc_info.value)

    def test_generate_questions_with_custom_prompt(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test generation with custom prompt."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            custom_prompt = "Generate questions about leadership only"
            question_bank = generator.generate_questions(prompt=custom_prompt, use_cache=False)

            assert isinstance(question_bank, QuestionBank)

            # Verify custom prompt was used (check both contents and string format)
            call_args = generator.client.models.generate_content.call_args
            contents = call_args.kwargs['contents']
            # Contents might be a string or list, check appropriately
            if isinstance(contents, str):
                assert custom_prompt in contents
            else:
                assert any(custom_prompt in str(content) for content in contents)

    def test_generate_questions_with_cache(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test generation with caching enabled."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            question_bank = generator.generate_questions(use_cache=True)

            assert isinstance(question_bank, QuestionBank)
            assert generator.cached_content is not None

    def test_generate_questions_without_cache(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test generation without caching."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            question_bank = generator.generate_questions(use_cache=False)

            assert isinstance(question_bank, QuestionBank)

    def test_generate_questions_custom_num_questions(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test generation with custom number of questions."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            question_bank = generator.generate_questions(num_questions_per_category=20)

            assert isinstance(question_bank, QuestionBank)


# ============================================================================
# CATEGORY GENERATION TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorCategoryGeneration:
    """Test category-based generation."""

    def test_generate_by_category_success(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test generating questions by category."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            category_prompts = {
                "leadership": "Generate leadership questions",
                "curriculum": "Generate curriculum questions"
            }

            question_bank = generator.generate_questions_by_category(category_prompts)

            assert isinstance(question_bank, QuestionBank)
            # Should call generate_content once per category
            assert generator.client.models.generate_content.call_count >= 2

    def test_generate_by_category_no_files(self, mock_env_vars):
        """Test category generation without files."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            with pytest.raises(ValueError):
                generator.generate_questions_by_category({"test": "prompt"})


# ============================================================================
# REGENERATION TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorRegeneration:
    """Test question regeneration."""

    def test_regenerate_with_different_prompt(
        self, mock_env_vars, mock_uploaded_files, mock_generate_response
    ):
        """Test regenerating questions with different prompt using real cache."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock real cache object (not dict)
            mock_cache = Mock()
            mock_cache.name = "cachedContents/test789"
            mock_cache.expire_time = "2025-01-01T14:00:00Z"
            generator.cached_content = mock_cache

            generator.client.models.generate_content = Mock(return_value=mock_generate_response)

            new_prompt = "Focus on legal aspects only"
            question_bank = generator.regenerate_with_different_prompt(new_prompt)

            assert isinstance(question_bank, QuestionBank)

            # Verify cache was used
            call_args = generator.client.models.generate_content.call_args
            config = call_args.kwargs['config']
            assert 'cached_content' in config
            assert config['cached_content'] == mock_cache.name


# ============================================================================
# FILE OPERATIONS TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorFileOperations:
    """Test file save and cleanup operations."""

    def test_save_to_file(self, mock_env_vars, sample_question_bank, temp_dir):
        """Test saving question bank to file."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            output_file = temp_dir / "output" / "questions.json"
            generator.save_to_file(sample_question_bank, str(output_file))

            assert output_file.exists()

            # Verify content
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert "categories" in data
            assert "questions" in data

    def test_save_to_file_default_path(self, mock_env_vars, sample_question_bank, monkeypatch, temp_dir):
        """Test saving with default output path."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            monkeypatch.chdir(temp_dir)
            generator = NQESHQuestionGenerator()

            generator.save_to_file(sample_question_bank)

            # Should create output directory and file
            expected_file = Path(config.OUTPUT_DIR) / config.QUESTIONS_OUTPUT_FILE
            assert expected_file.exists()

    def test_cleanup_files(self, mock_env_vars, mock_uploaded_files):
        """Test cleanup of uploaded files."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files
            generator.cached_content = {"test": "data"}

            generator.client.files.delete = Mock()

            generator.cleanup_files()

            # Should delete all uploaded files
            assert generator.client.files.delete.call_count == len(mock_uploaded_files)
            assert len(generator.uploaded_files) == 0
            assert generator.cached_content is None

    def test_cleanup_files_with_errors(self, mock_env_vars, mock_uploaded_files):
        """Test cleanup when deletion fails."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            generator.client.files.delete = Mock(side_effect=Exception("Delete failed"))

            # Should not raise exception
            generator.cleanup_files()

            assert len(generator.uploaded_files) == 0


# ============================================================================
# DISPLAY TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorDisplay:
    """Test display functionality."""

    def test_display_summary(self, mock_env_vars, sample_question_bank, capsys):
        """Test displaying question bank summary."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            generator.display_summary(sample_question_bank)

            captured = capsys.readouterr()
            assert "QUESTION BANK SUMMARY" in captured.out
            assert "Total Categories" in captured.out
            assert "Total Questions Generated" in captured.out

    def test_display_summary_empty_bank(self, mock_env_vars, capsys):
        """Test displaying summary for empty question bank."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()

            empty_bank = QuestionBank(categories=[], questions={})
            generator.display_summary(empty_bank)

            captured = capsys.readouterr()
            assert "Total Categories: 0" in captured.out


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
class TestGeneratorErrorHandling:
    """Test error handling in generator."""

    def test_api_error_during_generation(self, mock_env_vars, mock_uploaded_files):
        """Test handling of API errors during generation."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            generator.client.models.generate_content = Mock(
                side_effect=Exception("API Error")
            )

            with pytest.raises(Exception) as exc_info:
                generator.generate_questions()

            assert "API Error" in str(exc_info.value)

    def test_invalid_json_response(self, mock_env_vars, mock_uploaded_files):
        """Test handling of invalid JSON in API response."""
        with patch('src.nqesh_generator.core.generator.genai.Client'):
            generator = NQESHQuestionGenerator()
            generator.uploaded_files = mock_uploaded_files

            # Mock invalid JSON response
            mock_response = Mock()
            mock_response.text = "invalid json"
            generator.client.models.generate_content = Mock(return_value=mock_response)

            with pytest.raises(Exception):
                generator.generate_questions()
