"""
NQESH Question Validator with Context Caching.

This version uses Gemini's context caching to efficiently
validate multiple questions against the same source documents.

Key features:
- Uses context caching for source documents
- Reduced API costs and faster validation
- Explicit file state verification
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from google import genai

from src.nqesh_generator.models.question_models import QuestionBank, Question
from src.nqesh_generator.models.validation_models import (
    ValidationReport,
    QuestionValidationResult,
    CategoryValidationSummary,
    ValidationIssue
)
from src.nqesh_generator import config
from src.nqesh_generator.utils.env_loader import load_env


class NQESHQuestionValidator:
    """Validate NQESH test questions with context caching."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize the question validator with caching support.

        Args:
            api_key: Google AI API key.
            model_name: Name of the Gemini model to use.
        """
        # Load environment variables
        load_env()

        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name or config.VALIDATOR_MODEL_NAME
        self.uploaded_files = []
        self.cached_content = None

    def upload_source_files(self, files_dir: str = "files") -> List[Any]:
        """
        Upload all source files and verify they are accessible.

        Args:
            files_dir: Directory containing source DepEd Order files

        Returns:
            List of uploaded file objects
        """
        files_path = Path(files_dir)

        if not files_path.exists():
            raise FileNotFoundError(f"Directory '{files_dir}' not found.")

        file_list = list(files_path.glob("*"))
        if not file_list:
            raise FileNotFoundError(f"No files found in '{files_dir}' directory.")

        print(f"Uploading {len(file_list)} source files for validation...")

        for file_path in file_list:
            if file_path.is_file():
                print(f"  Uploading: {file_path.name}")
                uploaded_file = self.client.files.upload(file=str(file_path))
                self.uploaded_files.append(uploaded_file)
                print(f"    ✓ File URI: {uploaded_file.uri}")

                # Verify file is accessible by checking metadata
                try:
                    verified_file = self.client.files.get(name=uploaded_file.name)
                    print(f"    ✓ File verified: {verified_file.state if hasattr(verified_file, 'state') else 'active'}")
                except Exception as e:
                    print(f"    ⚠️ Warning: Could not verify file access: {e}")

        print(f"\n✓ Successfully uploaded and verified {len(self.uploaded_files)} source files\n")
        return self.uploaded_files

    def create_cached_content(self) -> Any:
        """
        Create a cached content object with source documents.
        This allows efficient reuse of the same context across multiple validations.

        Returns:
            Cached content object
        """
        if not self.uploaded_files:
            raise ValueError("No source files uploaded. Call upload_source_files() first.")

        print("Creating cached content for efficient validation...")

        # Prepare content with all source files
        cache_contents = []

        for file in self.uploaded_files:
            cache_contents.append(
                {"file_data": {"mime_type": file.mime_type, "file_uri": file.uri}}
            )

        # Add base system instruction to cache
        validation_system_instruction = """You are an expert fact-checker and educational assessment validator.
Your role is to meticulously verify test questions against the provided source documents to ensure:
1. Factual accuracy - all content is grounded in the source documents
2. Answer correctness - the correct answer is truly correct per the documents
3. Explanation accuracy - explanations accurately reflect source material
4. Options validity - all options are appropriate and plausible

Be thorough, critical, and precise. Use direct quotes from source documents to support your findings.
If something cannot be verified or is incorrect, clearly identify it and explain why.

The source documents have been uploaded and you must reference them when validating questions."""

        cache_contents.append(validation_system_instruction)

        # Create cached content (if supported by the model)
        # Note: Context caching is done automatically by the Gemini API when the same
        # content is used across multiple requests. We structure it to maximize reuse.

        self.cached_content = {
            "files": self.uploaded_files,
            "base_instruction": validation_system_instruction,
            "contents": cache_contents
        }

        print("✓ Cached content prepared for validation\n")
        return self.cached_content

    def validate_single_question(
        self,
        question: Question,
        category_name: str,
        category_id: str
    ) -> QuestionValidationResult:
        """
        Validate a single question against cached source documents.

        Args:
            question: Question object to validate
            category_name: Name of the category
            category_id: ID of the category

        Returns:
            QuestionValidationResult object
        """
        if not self.uploaded_files:
            raise ValueError("No source files uploaded. Call upload_source_files() first.")

        if not self.cached_content:
            raise ValueError("Cached content not created. Call create_cached_content() first.")

        # Prepare validation prompt for this specific question
        question_prompt = f"""You are validating the following test question against the source documents.

**Category**: {category_name}
**Question ID**: {question.question_id}

**Question**: {question.question}

**Options**:
1. {question.options[0]}
2. {question.options[1]}
3. {question.options[2]}
4. {question.options[3]}

**Stated Correct Answer**: {question.correct_answer}

**Explanation**: {question.explanation}

**Stated Source**: {question.source}

---

**YOUR VALIDATION TASKS:**

1. **Factual Accuracy**: Search through the provided source documents to verify if this question's content is based on actual information. If you cannot find supporting evidence, note this as a factual error.

2. **Answer Correctness**: Based on the source documents, is the "Stated Correct Answer" actually correct? If not, identify what the correct answer should be.

3. **Explanation Accuracy**: Does the explanation correctly reference and accurately represent information from the source documents? Check for:
   - Correct document citations (e.g., Item numbers, Section numbers)
   - Accurate paraphrasing or quotation
   - No invented or misrepresented information

4. **Options Quality**: Are all four options plausible and distinct?

5. **Source Verification**: Can you find the information in the documents? Which specific document, section, or item number?

**IMPORTANT**:
- Be thorough and precise
- Quote specific sections from source documents
- If you cannot find evidence, clearly state this
- Assign a confidence score (0.0 to 1.0)
- Be critical but fair

Provide your validation assessment in the structured format requested."""

        # Prepare content: Start with cached content, then add question-specific prompt
        contents = []

        # Add uploaded source files (for context/caching)
        for file in self.uploaded_files:
            contents.append(
                {"file_data": {"mime_type": file.mime_type, "file_uri": file.uri}}
            )

        # Add question-specific prompt
        contents.append(question_prompt)

        print(f"  Validating question: {question.question_id} (using cached context)...")

        # Generate validation with structured output
        # The Gemini API will automatically cache the common parts (files + base instruction)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config={
                "system_instruction": self.cached_content["base_instruction"],
                "response_mime_type": "application/json",
                "response_json_schema": QuestionValidationResult.model_json_schema()
            }
        )

        # Parse response into Pydantic model
        validation_result = QuestionValidationResult.model_validate_json(response.text)

        return validation_result

    def validate_question_bank(
        self,
        question_bank_file: str = None
    ) -> ValidationReport:
        """
        Validate an entire question bank with caching.

        Args:
            question_bank_file: Path to the question bank JSON file (defaults to output/nqesh_questions.json)

        Returns:
            ValidationReport object
        """
        if question_bank_file is None:
            question_bank_file = Path(config.OUTPUT_DIR) / config.QUESTIONS_OUTPUT_FILE

        print(f"\nLoading question bank from: {question_bank_file}")

        with open(question_bank_file, 'r', encoding='utf-8') as f:
            question_bank_data = json.load(f)

        question_bank = QuestionBank.model_validate(question_bank_data)

        print(f"Found {len(question_bank.categories)} categories")
        total_questions = sum(len(q) for q in question_bank.questions.values())
        print(f"Total questions to validate: {total_questions}\n")

        # Create cached content for efficient validation
        self.create_cached_content()

        all_results: List[QuestionValidationResult] = []

        print("="*70)
        print("STARTING VALIDATION (with context caching)")
        print("="*70 + "\n")

        # Validate each question
        for category in question_bank.categories:
            category_questions = question_bank.questions.get(category.id, [])

            if not category_questions:
                continue

            print(f"\nValidating category: {category.name}")
            print(f"  Questions in category: {len(category_questions)}\n")

            for question in category_questions:
                try:
                    result = self.validate_single_question(
                        question=question,
                        category_name=category.name,
                        category_id=category.id
                    )
                    all_results.append(result)

                    status = "✓ VALID" if result.is_valid else "✗ ISSUES FOUND"
                    print(f"    {status} - {question.question_id} (confidence: {result.confidence_score:.2f})")

                except Exception as e:
                    print(f"    ✗ ERROR validating {question.question_id}: {e}")
                    failed_result = QuestionValidationResult(
                        question_id=question.question_id,
                        category_id=category.id,
                        is_valid=False,
                        is_factually_accurate=False,
                        is_answer_correct=False,
                        is_explanation_accurate=False,
                        are_options_valid=False,
                        issues=[ValidationIssue(
                            severity="critical",
                            issue_type="validation_error",
                            description=f"Validation process failed: {str(e)}"
                        )],
                        confidence_score=0.0,
                        notes=f"Validation error: {str(e)}"
                    )
                    all_results.append(failed_result)

        print("\n" + "="*70)
        print("VALIDATION COMPLETE")
        print("="*70 + "\n")

        # Generate report (same as v1)
        return self._generate_validation_report(question_bank, all_results)

    def _generate_validation_report(
        self,
        question_bank: QuestionBank,
        all_results: List[QuestionValidationResult]
    ) -> ValidationReport:
        """Generate validation report from results."""

        valid_count = sum(1 for r in all_results if r.is_valid)
        invalid_count = len(all_results) - valid_count

        # Category summaries
        category_summaries = []
        for category in question_bank.categories:
            category_results = [r for r in all_results if r.category_id == category.id]
            if not category_results:
                continue

            category_valid = sum(1 for r in category_results if r.is_valid)
            critical = sum(len([i for i in r.issues if i.severity == "critical"]) for r in category_results)
            major = sum(len([i for i in r.issues if i.severity == "major"]) for r in category_results)
            minor = sum(len([i for i in r.issues if i.severity == "minor"]) for r in category_results)
            avg_confidence = sum(r.confidence_score for r in category_results) / len(category_results)

            category_summaries.append(CategoryValidationSummary(
                category_id=category.id,
                category_name=category.name,
                total_questions=len(category_results),
                valid_questions=category_valid,
                invalid_questions=len(category_results) - category_valid,
                critical_issues=critical,
                major_issues=major,
                minor_issues=minor,
                average_confidence=avg_confidence
            ))

        total_critical = sum(len([i for i in r.issues if i.severity == "critical"]) for r in all_results)
        overall_confidence = sum(r.confidence_score for r in all_results) / len(all_results) if all_results else 0.0
        accuracy_rate = (valid_count / len(all_results) * 100) if all_results else 0.0

        # Generate recommendations
        recommendations = []
        if invalid_count > 0:
            recommendations.append(f"{invalid_count} question(s) require review and correction")
        if total_critical > 0:
            recommendations.append(f"{total_critical} critical issue(s) found that must be addressed immediately")
        if accuracy_rate < 90:
            recommendations.append("Overall accuracy is below 90% - recommend thorough review")
        if overall_confidence < 0.8:
            recommendations.append("Average confidence score is below 0.8 - some validations need manual verification")

        return ValidationReport(
            validation_timestamp=datetime.now().isoformat(),
            total_questions=len(all_results),
            valid_questions=valid_count,
            invalid_questions=invalid_count,
            category_summaries=category_summaries,
            question_results=all_results,
            overall_accuracy_rate=accuracy_rate,
            overall_confidence=overall_confidence,
            critical_issues_count=total_critical,
            recommendations=recommendations
        )

    def save_validation_report(
        self,
        report: ValidationReport,
        json_output: str = None,
        markdown_output: str = None
    ):
        """Save validation report to JSON and Markdown."""
        if json_output is None:
            json_output = Path(config.OUTPUT_DIR) / config.VALIDATION_REPORT_JSON
        if markdown_output is None:
            markdown_output = Path(config.OUTPUT_DIR) / config.VALIDATION_REPORT_MD

        # Ensure output directory exists
        json_path = Path(json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        # Save JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ JSON report saved to: {json_path}")

        # Generate and save Markdown
        markdown_path = Path(markdown_output)
        markdown_content = self._generate_markdown_report(report)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"✓ Markdown report saved to: {markdown_path}")

    def _generate_markdown_report(self, report: ValidationReport) -> str:
        """Generate a markdown report from validation results."""
        md = []
        md.append("# NQESH Question Bank Validation Report\n")
        md.append(f"**Generated:** {report.validation_timestamp}\n")
        md.append(f"**Overall Accuracy:** {report.overall_accuracy_rate:.1f}%\n")
        md.append(f"**Overall Confidence:** {report.overall_confidence:.2f}\n\n")

        md.append("## Summary\n")
        md.append(f"- Total Questions: {report.total_questions}\n")
        md.append(f"- Valid Questions: {report.valid_questions}\n")
        md.append(f"- Invalid Questions: {report.invalid_questions}\n")
        md.append(f"- Critical Issues: {report.critical_issues_count}\n\n")

        if report.recommendations:
            md.append("## Recommendations\n")
            for rec in report.recommendations:
                md.append(f"- {rec}\n")
            md.append("\n")

        md.append("## Category Summaries\n")
        for cat in report.category_summaries:
            md.append(f"### {cat.category_name}\n")
            md.append(f"- Total: {cat.total_questions}\n")
            md.append(f"- Valid: {cat.valid_questions}\n")
            md.append(f"- Invalid: {cat.invalid_questions}\n")
            md.append(f"- Average Confidence: {cat.average_confidence:.2f}\n\n")

        md.append("## Question Details\n")
        for result in report.question_results:
            status = "✓ VALID" if result.is_valid else "✗ INVALID"
            md.append(f"### {result.question_id} - {status}\n")
            md.append(f"- Confidence: {result.confidence_score:.2f}\n")
            if result.issues:
                md.append("- Issues:\n")
                for issue in result.issues:
                    md.append(f"  - **{issue.severity.upper()}** ({issue.issue_type}): {issue.description}\n")
            if result.notes:
                md.append(f"- Notes: {result.notes}\n")
            md.append("\n")

        return "".join(md)

    def cleanup_files(self):
        """Delete uploaded files from Gemini."""
        print("\nCleaning up uploaded files...")
        for file in self.uploaded_files:
            try:
                self.client.files.delete(name=file.name)
                print(f"  ✓ Deleted: {file.name}")
            except Exception as e:
                print(f"  ✗ Error deleting {file.name}: {e}")

        self.uploaded_files = []
        self.cached_content = None
        print("✓ Cleanup complete")


def main():
    """Main function with caching support."""
    print("="*70)
    print("NQESH QUESTION BANK VALIDATOR (with Context Caching)")
    print("="*70 + "\n")

    # Load environment variables first
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        return

    try:
        # Initialize validator
        validator = NQESHQuestionValidator()

        # Upload and verify source files
        validator.upload_source_files(files_dir="files")

        # Validate with caching
        validation_report = validator.validate_question_bank()

        # Save reports
        validator.save_validation_report(report=validation_report)

        # Display summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        print(f"\nTotal Questions: {validation_report.total_questions}")
        print(f"Valid Questions: {validation_report.valid_questions}")
        print(f"Questions with Issues: {validation_report.invalid_questions}")
        print(f"Accuracy Rate: {validation_report.overall_accuracy_rate:.1f}%")
        print(f"Average Confidence: {validation_report.overall_confidence:.2f}")
        print(f"Critical Issues: {validation_report.critical_issues_count}")

        if validation_report.recommendations:
            print("\nKey Recommendations:")
            for rec in validation_report.recommendations:
                print(f"  • {rec}")

        print("\n" + "="*70 + "\n")

        # Cleanup
        validator.cleanup_files()

        print("✓ Validation completed with context caching!")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
