"""
Configuration file for NQESH Question Generator.

Modify these values to customize the question generation behavior.
"""

# Model Configuration
MODEL_NAME = "gemini-2.5-pro"
VALIDATOR_MODEL_NAME = "gemini-2.5-flash"

# Output Configuration
OUTPUT_DIR = "output"
QUESTIONS_OUTPUT_FILE = "nqesh_questions.json"
VALIDATION_REPORT_JSON = "validation_report.json"
VALIDATION_REPORT_MD = "validation_report.md"

# Question Generation Settings
DEFAULT_NUM_QUESTIONS_PER_CATEGORY = 10

# System Instruction
SYSTEM_INSTRUCTION = """You are an expert educational assessment designer specializing in creating test questions
for the National Qualifying Examination for School Heads (NQESH) in the Philippines.

Your task is to generate high-quality multiple-choice test questions based on DepEd Orders provided to you.

IMPORTANT RULES:
1. Only generate questions based on the content of the provided DepEd Order files
2. Do NOT invent questions that cannot be answered from the provided documents
3. Each question must have exactly 4 options
4. Provide clear, detailed explanations for correct answers
5. Use deped.gov.ph as the source URL (user will edit later)
6. Categories should be named after the DepEd Order titles or main topics
7. Questions should be relevant for aspiring school heads
8. Focus on leadership, management, curriculum, legal, ethical, and community relations aspects
9. Ensure questions test understanding, application, and analysis - not just recall
10. Make distractors (wrong options) plausible but clearly incorrect

Question Categories should align with NQESH competency areas:
- Educational Leadership (leadership theories, school management, administration)
- Curriculum and Instruction (curriculum development, instructional strategies, assessment)
- Human Resource Management (personnel management, teacher development)
- Legal and Ethical Foundations (education laws, policies, ethical standards)
- Community Relations and Partnerships (stakeholder engagement, collaboration)

Generate questions that reflect the complexity and depth required for school head positions.
"""

# Default Prompt Template
DEFAULT_PROMPT_TEMPLATE = """Based on the provided DepEd Order documents, generate comprehensive NQESH test questions.

Generate approximately {num_questions} questions for each relevant category you identify in the documents.

Requirements:
1. Create categories based on the DepEd Order topics (name each category after the DepEd Order or main topic)
2. Each question must be directly answerable from the provided documents
3. Questions should test higher-order thinking skills appropriate for school head candidates
4. Ensure variety in question types (comprehension, application, analysis)
5. Make sure all 4 options are plausible but only one is clearly correct
6. Provide detailed explanations that reference the source material
7. Use deped.gov.ph as the source URL

Focus on content relevant to:
- Leadership and management practices
- Curriculum and instructional policies
- Human resource management
- Legal frameworks and ethical standards
- Community relations and partnerships

Output the questions in the specified JSON structure."""
