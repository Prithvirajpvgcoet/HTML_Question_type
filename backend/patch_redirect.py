import os
import re

file_path = 'frontend-candidate/src/pages/CandidateTest/CandidateTestPage.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the redirect effect
old_effect = '''  useEffect(() => {
    if (!candidateName) {
      navigate(/login/, { replace: true });
    }
  }, [candidateName, navigate, questionId]);'''

new_effect = '''  useEffect(() => {
    if (!candidateName && !isSubmitted) {
      navigate(/login/, { replace: true });
    }
  }, [candidateName, navigate, questionId, isSubmitted]);'''

code = code.replace(old_effect, new_effect)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched candidateName redirect')
