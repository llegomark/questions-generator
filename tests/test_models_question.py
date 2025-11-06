"""
Unit tests for question models (question_models.py).

Tests cover:
- Model instantiation and validation
- Field constraints and validators
- Serialization/deserialization
- Edge cases and error handling
"""
import json
import pytest
from pydantic import ValidationError

from src.nqesh_generator.models.question_models import (
    Category, Question, QuestionBank
)


# ============================================================================
# CATEGORY MODEL TESTS
# ============================================================================

@pytest.mark.unit
class TestCategory:
    """Test Category model."""

    def test_category_creation_valid(self):
        """Test creating a valid category."""
        category = Category(
            id="test-category",
            name="Test Category",
            description="A test category description"
        )

        assert category.id == "test-category"
        assert category.name == "Test Category"
        assert category.description == "A test category description"

    def test_category_creation_minimal(self):
        """Test creating category with minimal required fields."""
        category = Category(
            id="minimal",
            name="Minimal",
            description="Desc"
        )

        assert category.id == "minimal"
        assert category.name == "Minimal"
        assert category.description == "Desc"

    def test_category_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Category(id="test", name="Test")  # Missing description

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('description',) for error in errors)

    def test_category_empty_strings(self):
        """Test category with empty string values."""
        # Empty strings are technically valid for string fields
        category = Category(id="", name="", description="")
        assert category.id == ""
        assert category.name == ""
        assert category.description == ""

    def test_category_serialization(self, sample_category):
        """Test category serialization to dict."""
        data = sample_category.model_dump()

        assert isinstance(data, dict)
        assert data["id"] == sample_category.id
        assert data["name"] == sample_category.name
        assert data["description"] == sample_category.description

    def test_category_json_serialization(self, sample_category):
        """Test category JSON serialization."""
        json_str = sample_category.model_dump_json()
        data = json.loads(json_str)

        assert data["id"] == sample_category.id
        assert data["name"] == sample_category.name
        assert data["description"] == sample_category.description

    def test_category_deserialization(self):
        """Test category deserialization from dict."""
        data = {
            "id": "test-id",
            "name": "Test Name",
            "description": "Test Description"
        }

        category = Category.model_validate(data)

        assert category.id == data["id"]
        assert category.name == data["name"]
        assert category.description == data["description"]

    def test_category_json_deserialization(self):
        """Test category deserialization from JSON string."""
        json_str = '{"id": "json-test", "name": "JSON Test", "description": "Test"}'
        category = Category.model_validate_json(json_str)

        assert category.id == "json-test"
        assert category.name == "JSON Test"

    def test_category_extra_fields_ignored(self):
        """Test that extra fields are ignored by default."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Desc",
            "extra_field": "ignored"
        }

        # Pydantic v2 ignores extra fields by default
        category = Category.model_validate(data)
        assert not hasattr(category, "extra_field")


# ============================================================================
# QUESTION MODEL TESTS
# ============================================================================

@pytest.mark.unit
class TestQuestion:
    """Test Question model."""

    def test_question_creation_valid(self, sample_question):
        """Test creating a valid question."""
        assert sample_question.question_id == "EL001"
        assert sample_question.question == "What is the primary role of a school head?"
        assert len(sample_question.options) == 4
        assert sample_question.correct_answer == "To provide instructional leadership"
        assert "instructional leadership" in sample_question.explanation
        assert "deped.gov.ph" in sample_question.source

    def test_question_exactly_four_options(self):
        """Test that questions must have exactly 4 options."""
        # Less than 4 options
        with pytest.raises(ValidationError) as exc_info:
            Question(
                question_id="Q001",
                question="Test?",
                options=["A", "B", "C"],  # Only 3 options
                correct_answer="A",
                explanation="Explanation",
                source="https://deped.gov.ph"
            )

        errors = exc_info.value.errors()
        assert any("options" in str(error) for error in errors)

    def test_question_more_than_four_options(self):
        """Test that questions cannot have more than 4 options."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                question_id="Q001",
                question="Test?",
                options=["A", "B", "C", "D", "E"],  # 5 options
                correct_answer="A",
                explanation="Explanation",
                source="https://deped.gov.ph"
            )

        errors = exc_info.value.errors()
        assert any("options" in str(error) for error in errors)

    def test_question_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                question_id="Q001",
                question="Test?"
                # Missing options, correct_answer, explanation, source
            )

        errors = exc_info.value.errors()
        error_fields = [error['loc'][0] for error in errors]
        assert 'options' in error_fields
        assert 'correct_answer' in error_fields
        assert 'explanation' in error_fields
        assert 'source' in error_fields

    def test_question_serialization(self, sample_question):
        """Test question serialization to dict."""
        data = sample_question.model_dump()

        assert isinstance(data, dict)
        assert data["question_id"] == sample_question.question_id
        assert data["question"] == sample_question.question
        assert data["options"] == sample_question.options
        assert data["correct_answer"] == sample_question.correct_answer
        assert data["explanation"] == sample_question.explanation
        assert data["source"] == sample_question.source

    def test_question_json_round_trip(self, sample_question):
        """Test question JSON serialization and deserialization round trip."""
        # Serialize to JSON
        json_str = sample_question.model_dump_json()

        # Deserialize back
        restored = Question.model_validate_json(json_str)

        assert restored.question_id == sample_question.question_id
        assert restored.question == sample_question.question
        assert restored.options == sample_question.options
        assert restored.correct_answer == sample_question.correct_answer
        assert restored.explanation == sample_question.explanation
        assert restored.source == sample_question.source

    def test_question_with_unicode(self):
        """Test question with Unicode characters."""
        question = Question(
            question_id="Q001",
            question="Ano ang pangunahing tungkulin ng punong-guro?",
            options=[
                "Magturo ng klase",
                "Magbigay ng pamumuno sa pagtuturo",
                "Mag-alaga ng gusali",
                "Pamahalaan ang pananalapi"
            ],
            correct_answer="Magbigay ng pamumuno sa pagtuturo",
            explanation="Ayon sa DepEd Order, ang pangunahing tungkulin ay pamumuno.",
            source="https://deped.gov.ph"
        )

        assert "Ano ang" in question.question
        assert "Magturo" in question.options[0]

    def test_question_correct_answer_not_in_options_allowed(self):
        """Test that correct_answer can be different from options (validation is logical, not strict)."""
        # Note: The model doesn't enforce that correct_answer must be in options
        # This is intentional to allow flexibility
        question = Question(
            question_id="Q001",
            question="Test?",
            options=["A", "B", "C", "D"],
            correct_answer="E",  # Not in options
            explanation="Explanation",
            source="https://deped.gov.ph"
        )

        assert question.correct_answer == "E"


# ============================================================================
# QUESTION BANK MODEL TESTS
# ============================================================================

@pytest.mark.unit
class TestQuestionBank:
    """Test QuestionBank model."""

    def test_question_bank_creation_valid(self, sample_question_bank):
        """Test creating a valid question bank."""
        assert len(sample_question_bank.categories) == 2
        assert len(sample_question_bank.questions) == 2
        assert "educational-leadership" in sample_question_bank.questions
        assert "curriculum-instruction" in sample_question_bank.questions

    def test_question_bank_empty(self):
        """Test creating an empty question bank."""
        bank = QuestionBank(categories=[], questions={})

        assert len(bank.categories) == 0
        assert len(bank.questions) == 0
        assert bank.questions == {}

    def test_question_bank_single_category(self, sample_category, sample_questions):
        """Test question bank with single category."""
        bank = QuestionBank(
            categories=[sample_category],
            questions={sample_category.id: sample_questions}
        )

        assert len(bank.categories) == 1
        assert bank.categories[0].id == sample_category.id
        assert len(bank.questions[sample_category.id]) == len(sample_questions)

    def test_question_bank_multiple_categories(self, sample_categories, sample_questions):
        """Test question bank with multiple categories."""
        bank = QuestionBank(
            categories=sample_categories,
            questions={
                cat.id: sample_questions for cat in sample_categories
            }
        )

        assert len(bank.categories) == len(sample_categories)
        assert len(bank.questions) == len(sample_categories)

    def test_question_bank_serialization(self, sample_question_bank):
        """Test question bank serialization."""
        data = sample_question_bank.model_dump()

        assert isinstance(data, dict)
        assert "categories" in data
        assert "questions" in data
        assert isinstance(data["categories"], list)
        assert isinstance(data["questions"], dict)

    def test_question_bank_json_round_trip(self, sample_question_bank):
        """Test question bank JSON round trip."""
        # Serialize
        json_str = sample_question_bank.model_dump_json()

        # Deserialize
        restored = QuestionBank.model_validate_json(json_str)

        assert len(restored.categories) == len(sample_question_bank.categories)
        assert len(restored.questions) == len(sample_question_bank.questions)

        # Check first category
        assert restored.categories[0].id == sample_question_bank.categories[0].id
        assert restored.categories[0].name == sample_question_bank.categories[0].name

        # Check first question in first category
        first_cat_id = sample_question_bank.categories[0].id
        assert len(restored.questions[first_cat_id]) == len(sample_question_bank.questions[first_cat_id])

    def test_question_bank_file_save_load(self, sample_question_bank, temp_dir):
        """Test saving and loading question bank from file."""
        file_path = temp_dir / "test_bank.json"

        # Save
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_question_bank.model_dump(), f, indent=2)

        # Load
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        restored = QuestionBank.model_validate(data)

        assert len(restored.categories) == len(sample_question_bank.categories)
        assert len(restored.questions) == len(sample_question_bank.questions)

    def test_question_bank_category_id_mismatch(self, sample_categories, sample_questions):
        """Test question bank where question dict keys don't match category IDs."""
        # This is allowed - questions dict can have different keys
        bank = QuestionBank(
            categories=sample_categories[:1],  # Only one category
            questions={
                "different-id": sample_questions,  # Different ID
                sample_categories[0].id: sample_questions
            }
        )

        assert len(bank.categories) == 1
        assert len(bank.questions) == 2  # Two entries in questions dict

    def test_question_bank_missing_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QuestionBank(categories=[])  # Missing questions

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('questions',) for error in errors)

    def test_question_bank_json_schema_generation(self):
        """Test that JSON schema can be generated for API use."""
        schema = QuestionBank.model_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "categories" in schema["properties"]
        assert "questions" in schema["properties"]

    def test_question_bank_with_large_dataset(self, sample_categories):
        """Test question bank with large number of questions."""
        # Generate 100 questions per category
        num_questions = 100
        questions_dict = {}

        for category in sample_categories:
            questions = [
                Question(
                    question_id=f"{category.id.upper()}{i:03d}",
                    question=f"Test question {i} for {category.name}?",
                    options=[f"Option A{i}", f"Option B{i}", f"Option C{i}", f"Option D{i}"],
                    correct_answer=f"Option A{i}",
                    explanation=f"Explanation for question {i}",
                    source="https://deped.gov.ph"
                )
                for i in range(1, num_questions + 1)
            ]
            questions_dict[category.id] = questions

        bank = QuestionBank(
            categories=sample_categories,
            questions=questions_dict
        )

        total_questions = sum(len(q) for q in bank.questions.values())
        assert total_questions == num_questions * len(sample_categories)
