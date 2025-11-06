# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered test question generator for the **National Qualifying Examination for School Heads (NQESH)** in the Philippines. The application uses Google's Gemini AI with context caching to generate and validate high-quality multiple-choice questions from DepEd Order documents.

## Key Commands

### Setup
```bash
./scripts/setup.sh
```
Creates virtual environment, installs dependencies, and initializes directory structure.

### Generate Questions
```bash
./scripts/run.sh
# Or manually:
source venv/bin/activate
python3 -m src.nqesh_generator.core.generator
```
Uploads files from `files/` directory, generates questions, and saves to `nqesh_questions.json`.

### Validate Questions
```bash
./scripts/run_validator.sh
# Or manually:
source venv/bin/activate
python3 -m src.nqesh_generator.core.validator
```
Validates generated questions against source documents, outputs `validation_report.json` and `validation_report.md`.

### Run Tests
```bash
source venv/bin/activate
pytest tests/
# Or run import verification:
python3 tests/test_imports.py
```

## Architecture

### Core Design Pattern: Context Caching

The application's central architecture revolves around **Gemini's context caching** to reduce API costs and latency:

1. **Upload Phase**: Source documents are uploaded once to Gemini's file API
2. **Cache Creation**: Documents + system instructions are cached as reusable context
3. **Generation/Validation**: Multiple operations reuse the cached context without re-uploading

This pattern is implemented in both `NQESHQuestionGenerator` and `NQESHQuestionValidator` classes.

### Module Organization

**src/nqesh_generator/** - Main package following src-layout pattern
- **config.py** - Configuration constants (model name, prompts, system instructions)
- **core/** - Business logic
  - `generator.py`: Question generation with caching (`NQESHQuestionGenerator`)
  - `validator.py`: Question validation with caching (`NQESHQuestionValidator`)
- **models/** - Pydantic data models for type safety
  - `question_models.py`: `Category`, `Question`, `QuestionBank`
  - `validation_models.py`: `ValidationIssue`, `QuestionValidationResult`, `ValidationReport`
- **utils/** - Helper utilities
  - `env_loader.py`: Environment variable management

### Key Classes and Methods

#### NQESHQuestionGenerator (core/generator.py)

Main workflow methods:
- `upload_files(files_dir)` - Upload documents and verify accessibility
- `create_cached_content()` - Create cached context for efficient reuse
- `generate_questions(prompt, num_questions, use_cache)` - Generate questions using cached context
- `generate_questions_by_category(category_prompts)` - Generate questions category-by-category
- `regenerate_with_different_prompt(new_prompt)` - Iterate on generation without re-uploading
- `save_to_file(question_bank, output_file)` - Serialize to JSON
- `cleanup_files()` - Delete uploaded files from Gemini

#### NQESHQuestionValidator (core/validator.py)

Main workflow methods:
- `upload_source_files(files_dir)` - Upload source documents for validation
- `create_cached_content()` - Cache source documents
- `validate_question_bank(question_bank_file)` - Validate all questions using cached context
- `save_validation_report(report)` - Generate JSON and Markdown reports

### Data Flow

1. **Generation Flow**:
   ```
   upload_files() → create_cached_content() → generate_questions() → save_to_file()
   ```

2. **Validation Flow**:
   ```
   upload_source_files() → create_cached_content() → validate_question_bank() → save_validation_report()
   ```

### Structured Output with Pydantic

The application uses Pydantic models to enforce structured JSON output from Gemini:
- Models define schema with Field descriptions
- `model_json_schema()` generates JSON schema for Gemini API
- `model_validate_json()` parses and validates responses
- `model_dump()` serializes for file output

This ensures type-safe, validated data throughout the pipeline.

## Configuration

Edit `src/nqesh_generator/config.py` to customize:
- `MODEL_NAME`: Gemini model (default: "gemini-2.5-pro")
- `DEFAULT_NUM_QUESTIONS_PER_CATEGORY`: Questions per category (default: 10)
- `SYSTEM_INSTRUCTION`: AI behavior for question generation
- `DEFAULT_PROMPT_TEMPLATE`: Template for question requests

## Environment Setup

The application requires:
- Python 3.8+
- Google Gemini API key in `.env` file:
  ```
  GEMINI_API_KEY=your-api-key-here
  ```
- Source documents in `files/` directory

The `env_loader.py` utility handles environment variable loading with fallback to system environment.

## Output Files

- `nqesh_questions.json` - Generated question bank with categories and questions
- `validation_report.json` - Detailed validation results (JSON)
- `validation_report.md` - Human-readable validation report (Markdown)

## Import Pattern

The project uses src-layout, so imports follow this pattern:
```python
from src.nqesh_generator.core.generator import NQESHQuestionGenerator
from src.nqesh_generator.models.question_models import QuestionBank
from src.nqesh_generator import config
```

All modules should be imported using full paths from the `src` directory.

## Development Notes

### Testing New Prompts
Use the caching methods to iterate quickly:
```python
generator = NQESHQuestionGenerator()
generator.upload_files()
generator.create_cached_content()  # Cache once

# Try different prompts without re-uploading
bank1 = generator.regenerate_with_different_prompt("Focus on legal aspects")
bank2 = generator.regenerate_with_different_prompt("Focus on leadership")
```

### Category-Based Generation
For large document sets, generate questions incrementally:
```python
category_prompts = {
    "educational-leadership": "Generate leadership questions...",
    "curriculum": "Generate curriculum questions..."
}
bank = generator.generate_questions_by_category(category_prompts)
```

### File Cleanup
Always clean up uploaded files when done to avoid quota issues:
```python
generator.cleanup_files()
validator.cleanup_files()
```

## Project Context

This tool is designed for **Philippine DepEd officials and educators** to create practice exams for the NQESH certification. Questions must:
- Be answerable from provided DepEd Order documents
- Test higher-order thinking (not just recall)
- Align with NQESH competency areas (leadership, curriculum, HR, legal, community)
- Have 4 plausible options with detailed explanations
- Use deped.gov.ph as source URL placeholder
