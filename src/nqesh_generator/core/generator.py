"""
NQESH Test Question Generator with Context Caching.

This version uses Gemini's context caching to efficiently
generate questions across multiple runs or iterations.

Features:
- Explicit context caching for source documents using Gemini Caching API
- File state verification after upload
- Support for multiple generation runs with same files
- Optimized for iterative prompt development
- Reduced API costs for repeated generations (cached tokens are cheaper)
"""
import os
import json
from pathlib import Path
from typing import List, Optional, Any
from google import genai
from google.genai import types

from src.nqesh_generator.models.question_models import QuestionBank, Category, Question
from src.nqesh_generator import config
from src.nqesh_generator.utils.env_loader import load_env


class NQESHQuestionGenerator:
    """Generate NQESH test questions with context caching."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        default_num_questions: Optional[int] = None
    ):
        """
        Initialize the question generator with caching support.

        Args:
            api_key: Google AI API key. If not provided, uses GEMINI_API_KEY environment variable.
            model_name: Name of the Gemini model to use. If not provided, uses config.MODEL_NAME
            system_instruction: Custom system instruction. If not provided, uses config.SYSTEM_INSTRUCTION
            default_num_questions: Default number of questions to generate per category.
        """
        # Load environment variables
        load_env()

        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name or config.MODEL_NAME
        self.system_instruction = system_instruction or config.SYSTEM_INSTRUCTION
        self.default_num_questions = default_num_questions or config.DEFAULT_NUM_QUESTIONS_PER_CATEGORY
        self.uploaded_files = []
        self.cached_content = None  # Will hold the actual Gemini CachedContent object

    def upload_files(self, files_dir: str = "files") -> List[Any]:
        """
        Upload all files and verify they are accessible.

        Args:
            files_dir: Directory containing DepEd Order files

        Returns:
            List of uploaded file objects
        """
        files_path = Path(files_dir)

        if not files_path.exists():
            raise FileNotFoundError(
                f"Directory '{files_dir}' not found. Please create it and add DepEd Order files.")

        file_list = list(files_path.glob("*"))
        if not file_list:
            raise FileNotFoundError(
                f"No files found in '{files_dir}' directory. Please add DepEd Order files.")

        print(f"Uploading {len(file_list)} files from '{files_dir}'...")

        for file_path in file_list:
            if file_path.is_file():
                # Skip hidden files and files without extensions (like .gitkeep)
                if file_path.name.startswith('.'):
                    print(f"  Skipping hidden file: {file_path.name}")
                    continue

                try:
                    print(f"  Uploading: {file_path.name}")
                    uploaded_file = self.client.files.upload(file=str(file_path))
                    self.uploaded_files.append(uploaded_file)
                    print(f"    ✓ File URI: {uploaded_file.uri}")

                    # Verify file is accessible
                    try:
                        verified_file = self.client.files.get(name=uploaded_file.name)
                        state = verified_file.state if hasattr(verified_file, 'state') else 'ACTIVE'
                        print(f"    ✓ File verified: {state}")
                    except Exception as e:
                        print(f"    ⚠️ Warning: Could not verify file access: {e}")
                except Exception as e:
                    print(f"    ✗ Error uploading {file_path.name}: {e}")
                    print(f"    Skipping this file and continuing...")

        print(f"\n✓ Successfully uploaded and verified {len(self.uploaded_files)} files\n")
        return self.uploaded_files

    def create_cached_content(self, ttl: str = "3600s") -> Any:
        """
        Create a cached content object using Gemini's Caching API.
        This allows efficient reuse when generating questions multiple times.

        The cache stores:
        - All uploaded source documents
        - System instruction

        Args:
            ttl: Time-to-live for the cache (e.g., "3600s" = 1 hour, "7200s" = 2 hours)
                 Default is 1 hour. Max is 1 hour for free tier.

        Returns:
            CachedContent object from Gemini API
        """
        if not self.uploaded_files:
            raise ValueError("No files uploaded. Call upload_files() first.")

        print("Creating cached content using Gemini Caching API...")
        print(f"  Cache TTL: {ttl}")

        # Prepare content with all source files
        cache_contents = []

        # Add all uploaded files to cache as Content objects
        for file in self.uploaded_files:
            cache_contents.append(
                types.Part.from_uri(
                    file_uri=file.uri,
                    mime_type=file.mime_type
                )
            )

        # Create the cache using Gemini's Caching API
        try:
            self.cached_content = self.client.caches.create(
                model=self.model_name,
                config=types.CreateCachedContentConfig(
                    display_name=f"nqesh_question_gen_{len(self.uploaded_files)}_files",
                    system_instruction=self.system_instruction,
                    contents=cache_contents,
                    ttl=ttl,
                )
            )

            print(f"✓ Cache created successfully!")
            print(f"  Cache name: {self.cached_content.name}")
            print(f"  Expires: {self.cached_content.expire_time}")
            print("  → Multiple generations will reuse this cached context\n")

            return self.cached_content

        except Exception as e:
            print(f"⚠️ Warning: Could not create cache: {e}")
            print("  Falling back to non-cached generation (still works, just not optimized)\n")
            self.cached_content = None
            return None

    def generate_questions(
        self,
        prompt: Optional[str] = None,
        num_questions_per_category: Optional[int] = None,
        use_cache: bool = True
    ) -> QuestionBank:
        """
        Generate test questions based on uploaded files with caching support.

        Args:
            prompt: Optional custom prompt. If not provided, uses default.
            num_questions_per_category: Number of questions to generate per category.
            use_cache: Whether to use cached content. Default True.

        Returns:
            QuestionBank object containing categories and questions
        """
        if not self.uploaded_files:
            raise ValueError("No files uploaded. Call upload_files() first.")

        # Create cached content if using cache and not yet created
        if use_cache and not self.cached_content:
            self.create_cached_content()

        # Use instance default if not specified
        num_questions = num_questions_per_category or self.default_num_questions

        # Use default prompt template from config
        default_prompt = config.DEFAULT_PROMPT_TEMPLATE.format(num_questions=num_questions)
        prompt_to_use = prompt or default_prompt

        # Prepare generation config
        generation_config = {
            "response_mime_type": "application/json",
            "response_json_schema": QuestionBank.model_json_schema()
        }

        # Use cached content if available
        if use_cache and self.cached_content:
            print(f"Generating questions using {self.model_name} (with Gemini cache)...")
            print("  → Using cached context (files + system instruction)")
            generation_config["cached_content"] = self.cached_content.name

            # When using cache, only send the new prompt
            contents = prompt_to_use
        else:
            # Standard generation without cache
            print(f"Generating questions using {self.model_name} (without cache)...")

            # Need to include files and system instruction in every call
            contents = []
            for file in self.uploaded_files:
                contents.append(
                    types.Part.from_uri(
                        file_uri=file.uri,
                        mime_type=file.mime_type
                    )
                )
            contents.append(prompt_to_use)
            generation_config["system_instruction"] = self.system_instruction

        print("This may take a few moments as the model analyzes the documents...\n")

        # Generate content with structured output
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generation_config
        )

        # Display token usage if using cache
        if use_cache and self.cached_content and hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            if hasattr(usage, 'cached_content_token_count'):
                print(f"  💰 Cached tokens used: {usage.cached_content_token_count}")
                print(f"  📝 New tokens processed: {usage.prompt_token_count}")
                print(f"  💡 Output tokens: {usage.candidates_token_count}\n")

        # Parse response into Pydantic model
        question_bank = QuestionBank.model_validate_json(response.text)

        print("✓ Questions generated successfully!\n")
        return question_bank

    def generate_questions_by_category(
        self,
        category_prompts: dict[str, str],
        num_questions_per_category: Optional[int] = None
    ) -> QuestionBank:
        """
        Generate questions category by category with caching.
        Useful for generating questions in smaller batches.

        Args:
            category_prompts: Dictionary mapping category names to specific prompts
            num_questions_per_category: Number of questions per category

        Returns:
            QuestionBank with all categories combined
        """
        if not self.uploaded_files:
            raise ValueError("No files uploaded. Call upload_files() first.")

        # Create cache once for all categories
        if not self.cached_content:
            self.create_cached_content()

        num_questions = num_questions_per_category or self.default_num_questions

        all_categories = []
        all_questions = {}

        print("="*70)
        print("GENERATING QUESTIONS BY CATEGORY (with cached context)")
        print("="*70 + "\n")

        for category_name, category_prompt in category_prompts.items():
            print(f"Generating questions for: {category_name}")

            # Generate for this category using cached context
            prompt = f"""{category_prompt}

Generate {num_questions} questions for the category: {category_name}

Output in the standard QuestionBank format."""

            question_bank = self.generate_questions(
                prompt=prompt,
                num_questions_per_category=num_questions,
                use_cache=True  # Reuse cached files
            )

            # Collect results
            for category in question_bank.categories:
                all_categories.append(category)
                if category.id in question_bank.questions:
                    all_questions[category.id] = question_bank.questions[category.id]

            print(f"  ✓ Generated {len(question_bank.questions.get(question_bank.categories[0].id, []))} questions\n")

        # Combine into single question bank
        combined_bank = QuestionBank(
            categories=all_categories,
            questions=all_questions
        )

        print("="*70)
        print("✓ All categories generated successfully!")
        print("="*70 + "\n")

        return combined_bank

    def regenerate_with_different_prompt(
        self,
        new_prompt: str,
        num_questions_per_category: Optional[int] = None
    ) -> QuestionBank:
        """
        Regenerate questions with a different prompt using cached files.
        Useful for iterating on question generation.

        Args:
            new_prompt: New prompt template to use
            num_questions_per_category: Number of questions per category

        Returns:
            QuestionBank with newly generated questions
        """
        print("Regenerating questions with new prompt (using cached context)...\n")

        return self.generate_questions(
            prompt=new_prompt,
            num_questions_per_category=num_questions_per_category,
            use_cache=True
        )

    def save_to_file(self, question_bank: QuestionBank, output_file: str = None):
        """
        Save the question bank to a JSON file.

        Args:
            question_bank: QuestionBank object to save
            output_file: Output file path (defaults to output/nqesh_questions.json)
        """
        if output_file is None:
            output_file = Path(config.OUTPUT_DIR) / config.QUESTIONS_OUTPUT_FILE

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(question_bank.model_dump(), f,
                      indent=2, ensure_ascii=False)

        print(f"✓ Questions saved to: {output_path}")

    def cleanup_files(self):
        """Delete uploaded files and cached content from Gemini."""
        print("\nCleaning up...")

        # Delete cache first
        if self.cached_content:
            try:
                self.client.caches.delete(name=self.cached_content.name)
                print(f"  ✓ Deleted cache: {self.cached_content.name}")
            except Exception as e:
                print(f"  ✗ Error deleting cache: {e}")

        # Delete uploaded files
        for file in self.uploaded_files:
            try:
                self.client.files.delete(name=file.name)
                print(f"  ✓ Deleted file: {file.name}")
            except Exception as e:
                print(f"  ✗ Error deleting {file.name}: {e}")

        self.uploaded_files = []
        self.cached_content = None
        print("✓ Cleanup complete")

    def display_summary(self, question_bank: QuestionBank):
        """
        Display a summary of generated questions.

        Args:
            question_bank: QuestionBank object to summarize
        """
        print("\n" + "="*70)
        print("QUESTION BANK SUMMARY")
        print("="*70)

        print(f"\nTotal Categories: {len(question_bank.categories)}")
        print("\nCategories:")
        for category in question_bank.categories:
            num_questions = len(question_bank.questions.get(category.id, []))
            print(
                f"  • {category.name} ({category.id}): {num_questions} questions")
            print(f"    {category.description}")

        total_questions = sum(len(q) for q in question_bank.questions.values())
        print(f"\nTotal Questions Generated: {total_questions}")

        # Display first question from first category as sample
        if question_bank.categories and question_bank.questions:
            first_category = question_bank.categories[0]
            first_questions = question_bank.questions.get(
                first_category.id, [])
            if first_questions:
                print("\n" + "-"*70)
                print("SAMPLE QUESTION")
                print("-"*70)
                q = first_questions[0]
                print(f"\nID: {q.question_id}")
                print(f"Category: {first_category.name}")
                print(f"\nQuestion: {q.question}")
                print("\nOptions:")
                for i, option in enumerate(q.options, 1):
                    marker = "✓" if option == q.correct_answer else " "
                    print(f"  {marker} {i}. {option}")
                print(f"\nExplanation: {q.explanation}")
                print(f"Source: {q.source}")

        print("\n" + "="*70 + "\n")


def main():
    """Main function demonstrating question generator features."""
    print("="*70)
    print("NQESH TEST QUESTION GENERATOR (with Context Caching)")
    print("National Qualifying Examination for School Heads")
    print("="*70 + "\n")

    # Load environment variables first
    load_env()

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Please set it using: export GEMINI_API_KEY='your-api-key'")
        return

    try:
        # Initialize generator
        generator = NQESHQuestionGenerator()

        # Upload files from 'files' directory
        generator.upload_files(files_dir="files")

        # Create cached content (explicit caching)
        generator.create_cached_content()

        # Generate questions (uses cached context)
        question_bank = generator.generate_questions()

        # Display summary
        generator.display_summary(question_bank)

        # Save to file
        generator.save_to_file(question_bank)

        # Optional: Demonstrate regeneration with cached context
        print("\n" + "="*70)
        print("CACHING BENEFIT DEMONSTRATION")
        print("="*70 + "\n")
        print("You can now regenerate questions with different settings")
        print("without re-uploading files:")
        print("  • Different number of questions")
        print("  • Different prompts")
        print("  • Different categories")
        print("\nThe cached context (files + instructions) will be reused!")
        print("\nExample:")
        print("  generator.regenerate_with_different_prompt('Focus on legal aspects')")
        print()

        # Cleanup
        generator.cleanup_files()

        print("\n✓ Process completed successfully!")
        print(f"\nYou can now edit the source URLs in '{Path(config.OUTPUT_DIR) / config.QUESTIONS_OUTPUT_FILE}' as needed.")

    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nPlease ensure:")
        print("  1. Create a 'files' directory in the same location as this script")
        print("  2. Add DepEd Order documents (PDF, TXT, etc.) to the 'files' directory")
        print("  3. Run the script again")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
