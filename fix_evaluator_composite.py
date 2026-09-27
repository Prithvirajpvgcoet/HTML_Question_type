import re

with open('backend/services/evaluation_service/evaluator.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's replace _values_equivalent and _is_style_match to handle composite properties robustly
replacement = '''
    def _extract_tokens(self, v: str):
        # Extract all floats and rgba/rgb colors in order
        tokens = []
        # Find all numbers and colors
        parts = re.split(r'(rgba?\([^)]+\)|-?\d+(?:\.\d+)?(?:px|em|rem|%|deg|s|ms)?)', v)
        for part in parts:
            part = part.strip()
            if not part: continue
            
            # Check if color
            rgba = self._parse_rgba(part)
            if rgba:
                tokens.append(("color", rgba))
                continue
                
            # Check if number
            num = self._extract_number(part)
            if num is not None:
                tokens.append(("number", num))
                continue
                
            # Otherwise just a string token
            if part != ',' and part != '':
                tokens.append(("string", part))
                
        return tokens

    def _values_equivalent(self, a: str, b: str, tolerance: float = 0.5) -> bool:
        if not a or not b: return False
        a, b = str(a).strip().lower(), str(b).strip().lower()
        if a == b: return True

        tokens_a = self._extract_tokens(a)
        tokens_b = self._extract_tokens(b)
        
        if not tokens_a or not tokens_b or len(tokens_a) != len(tokens_b):
            return False
            
        for (type_a, val_a), (type_b, val_b) in zip(tokens_a, tokens_b):
            if type_a != type_b: return False
            if type_a == "number":
                if abs(val_a - val_b) > tolerance: return False
            elif type_a == "color":
                if not all(abs(x - y) <= 1 for x, y in zip(val_a[:3], val_b[:3])): return False
                if abs(val_a[3] - val_b[3]) > 0.01: return False
            else:
                if val_a != val_b: return False
                
        return True

    def _is_style_match(self, prop: str, actual: str, expected_canonical: str) -> bool:
        # Now we apply fuzzy token equivalence to ALL computed styles
        return self._values_equivalent(actual, expected_canonical, tolerance=0.5)
'''

# The original has _extract_number, _parse_rgba, _values_equivalent, _is_style_match
import re as regex

# Find the block from _extract_number to the end of _is_style_match
pattern = regex.compile(r'    def _extract_number\(self, v: str\):.*?def _is_style_match.*?return str\(actual\)\.strip\(\)\.lower\(\) == str\(expected_canonical\)\.strip\(\)\.lower\(\)', regex.DOTALL)

match = pattern.search(text)
if match:
    # We will keep _extract_number and _parse_rgba, but replace the rest
    
    new_methods = '''    def _extract_number(self, v: str):
        m = re.fullmatch(r"-?\d+(\.\d+)?\s*(px|em|rem|%|deg|s|ms)?", v)
        return float(m.group(0).split()[0].rstrip("pxemr%dgs")) if m else None

    def _parse_rgba(self, v: str):
        m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", v)
        if not m:
            return None
        return [float(x) if x is not None else 1.0 for x in m.groups()]
''' + replacement

    text = text[:match.start()] + new_methods + text[match.end():]
    
    with open('backend/services/evaluation_service/evaluator.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully replaced _is_style_match and _values_equivalent.")
else:
    print("Could not find the block to replace.")
