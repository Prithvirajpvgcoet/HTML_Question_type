import os

file_path = 'frontend-candidate/src/pages/CandidateTest/CandidateTestPage.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    '  const executeSubmit = async () => {\n    submitFnRef.current = executeSubmit;',
    '  const executeSubmit = async () => {'
)
code = code.replace(
    '  const executeSubmit = async () => {',
    '  submitFnRef.current = executeSubmit;\n\n  const executeSubmit = async () => {'
)
# Fix the order because const executeSubmit can't be used before initialization
code = code.replace(
    '  submitFnRef.current = executeSubmit;\n\n  const executeSubmit = async () => {',
    '  const executeSubmit = async () => {'
)

# Insert after declaration!
parts = code.split('  const executeSubmit = async () => {')
part1 = parts[0] + '  const executeSubmit = async () => {'
part2 = parts[1]

# find end of executeSubmit (approx where it says   }; and then   if (isSubmitted) {)
end_idx = part2.find('  };')
part2 = part2[:end_idx + 4] + '\n  submitFnRef.current = executeSubmit;\n' + part2[end_idx + 4:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(part1 + part2)
print('Patched submitFnRef properly')
