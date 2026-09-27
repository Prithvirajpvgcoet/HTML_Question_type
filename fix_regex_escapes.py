import re

with open('backend/services/evaluation_service/evaluator.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the regex escapes in evaluator.py
text = text.replace(r're.split(r\'(rgba?\([^)]+\)|-?\d+(?:\.\d+)?(?:px|em|rem|%|deg|s|ms)?)\', v)', r're.split(r"(rgba?\([^)]+\)|-?\d+(?:\.\d+)?(?:px|em|rem|%|deg|s|ms)?)", v)')
text = text.replace(r're.fullmatch(r"-?\d+(\.\d+)?\s*(px|em|rem|%|deg|s|ms)?", v)', r're.fullmatch(r"-?\d+(?:\.\d+)?\s*(?:px|em|rem|%|deg|s|ms)?", v)')

with open('backend/services/evaluation_service/evaluator.py', 'w', encoding='utf-8') as f:
    f.write(text)
