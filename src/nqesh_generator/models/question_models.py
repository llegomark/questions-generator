"""
Pydantic models for NQESH test question generation structured output.
"""
from typing import List
from pydantic import BaseModel, Field


class Category(BaseModel):
    """Represents a test question category."""
    id: str = Field(
        description="Unique identifier for the category (kebab-case)")
    name: str = Field(description="Display name of the category")
    description: str = Field(
        description="Detailed description of what the category covers")


class Question(BaseModel):
    """Represents a single test question."""
    question_id: str = Field(
        description="Unique identifier for the question (e.g., EL001)")
    question: str = Field(description="The actual question text")
    options: List[str] = Field(
        min_length=4,
        max_length=4,
        description="List of 4 answer options"
    )
    correct_answer: str = Field(
        description="The correct answer from the options")
    explanation: str = Field(
        description="Detailed explanation of why this is the correct answer")
    source: str = Field(
        description="Source URL, use deped.gov.ph website only")


class QuestionBank(BaseModel):
    """Complete question bank with categories and questions."""
    categories: List[Category] = Field(
        description="List of question categories based on DepEd Orders")
    questions: dict[str, List[Question]] = Field(
        description="Dictionary mapping category IDs to lists of questions for that category"
    )
