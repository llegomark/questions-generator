"""
Test that all modules can be imported correctly.
"""
import sys
from pathlib import Path

# Add project root to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_import_models():
    """Test that model imports work."""
    from src.nqesh_generator.models.question_models import (
        Category, Question, QuestionBank
    )
    from src.nqesh_generator.models.validation_models import (
        ValidationIssue, QuestionValidationResult, ValidationReport
    )
    assert Category is not None
    assert Question is not None
    assert QuestionBank is not None
    assert ValidationIssue is not None
    assert QuestionValidationResult is not None
    assert ValidationReport is not None


def test_import_core():
    """Test that core module imports work."""
    from src.nqesh_generator.core.generator import NQESHQuestionGenerator
    from src.nqesh_generator.core.validator import NQESHQuestionValidator

    assert NQESHQuestionGenerator is not None
    assert NQESHQuestionValidator is not None


def test_import_config():
    """Test that config imports work."""
    from src.nqesh_generator import config

    assert config.MODEL_NAME is not None
    assert config.DEFAULT_NUM_QUESTIONS_PER_CATEGORY is not None
    assert config.SYSTEM_INSTRUCTION is not None


def test_import_utils():
    """Test that utils imports work."""
    from src.nqesh_generator.utils.env_loader import load_env

    assert load_env is not None


if __name__ == "__main__":
    print("Testing imports...")

    try:
        test_import_models()
        print("✓ Model imports successful")

        test_import_core()
        print("✓ Core imports successful")

        test_import_config()
        print("✓ Config imports successful")

        test_import_utils()
        print("✓ Utils imports successful")

        print("\n✓ All imports working correctly!")

    except Exception as e:
        print(f"\n✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
