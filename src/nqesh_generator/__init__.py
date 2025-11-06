"""
NQESH Test Question Generator and Validator.

A Python package for generating and validating test questions
for the National Qualifying Examination for School Heads (NQESH).
"""

__version__ = "1.0.0"
__author__ = "NQESH Development Team"

from src.nqesh_generator.core.generator import NQESHQuestionGenerator
from src.nqesh_generator.core.validator import NQESHQuestionValidator

__all__ = [
    "NQESHQuestionGenerator",
    "NQESHQuestionValidator",
]
