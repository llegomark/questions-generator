"""
Pydantic models for question validation and accuracy checking.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Represents a validation issue found in a question."""
    severity: Literal["critical", "major", "minor"] = Field(
        description="Severity level: 'critical', 'major', or 'minor'"
    )
    issue_type: Literal[
        "factual_error",
        "answer_mismatch",
        "explanation_incorrect",
        "source_not_found",
        "option_issues",
        "validation_error"
    ] = Field(
        description="Type of issue: 'factual_error', 'answer_mismatch', 'explanation_incorrect', 'source_not_found', 'option_issues', 'validation_error'"
    )
    description: str = Field(
        description="Detailed description of the issue found"
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Relevant excerpt from source documents that contradicts the question or supports the issue"
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Suggested correction or improvement"
    )


class QuestionValidationResult(BaseModel):
    """Result of validating a single question."""
    question_id: str = Field(
        description="ID of the question being validated"
    )
    category_id: str = Field(
        description="Category ID the question belongs to"
    )
    is_valid: bool = Field(
        description="Whether the question passed validation"
    )
    is_factually_accurate: bool = Field(
        description="Whether the question content is found in source documents"
    )
    is_answer_correct: bool = Field(
        description="Whether the correct answer is actually correct based on source documents"
    )
    is_explanation_accurate: bool = Field(
        description="Whether the explanation matches the source material"
    )
    are_options_valid: bool = Field(
        description="Whether all options are plausible and distinct"
    )
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="List of issues found during validation"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0 on the validation assessment"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes or context about this validation"
    )


class CategoryValidationSummary(BaseModel):
    """Summary of validation results for a category."""
    category_id: str
    category_name: str
    total_questions: int
    valid_questions: int
    invalid_questions: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    average_confidence: float = Field(ge=0.0, le=1.0)


class BatchValidationResult(BaseModel):
    """Result of validating multiple questions in a batch."""
    results: List[QuestionValidationResult] = Field(
        description="List of validation results for each question in the batch"
    )


class ValidationReport(BaseModel):
    """Complete validation report for the entire question bank."""
    validation_timestamp: str = Field(
        description="ISO timestamp when validation was performed"
    )
    total_questions: int = Field(
        description="Total number of questions validated"
    )
    valid_questions: int = Field(
        description="Number of questions that passed validation"
    )
    invalid_questions: int = Field(
        description="Number of questions with issues"
    )
    category_summaries: List[CategoryValidationSummary] = Field(
        description="Summary statistics per category"
    )
    question_results: List[QuestionValidationResult] = Field(
        description="Detailed validation results for each question"
    )
    overall_accuracy_rate: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of questions that are factually accurate"
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Average confidence score across all validations"
    )
    critical_issues_count: int = Field(
        description="Total count of critical issues requiring immediate attention"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="High-level recommendations based on validation results"
    )
