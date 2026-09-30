import os
import re

file_path = 'frontend-candidate/src/pages/CandidateTest/CandidateTestPage.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace executeSubmit
old_exec = r'const executeSubmit = async \(\) => \{\s*if \(submitting \|\| isSubmitted\) return;\s*setShowConfirm\(false\);\s*setSubmitting\(true\);'
new_exec = '''const submittedRef = useRef(false);
  const submitFnRef = useRef<() => void>(() => {});

  const executeSubmit = async () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    setShowConfirm(false);
    setSubmitting(true);'''
code = re.sub(old_exec, new_exec, code)

code = code.replace(
    'setSubmitting(false);\n      }',
    'submittedRef.current = false;\n        setSubmitting(false);\n      }'
)

code = code.replace(
    'const { candidateName, candidateEmail, token } = useCandidateStore();',
    'const { candidateName, candidateEmail, token, clearCandidateInfo } = useCandidateStore();'
)
code = code.replace(
    'setIsSubmitted(true);',
    'setIsSubmitted(true);\n              clearCandidateInfo();'
)

# Update the effect timer
old_timer = r'api\.get\(/invites/\$\{token\}\)\.then\(res => \{.*?\}\)\.catch\(\(\) => \{'
new_timer = '''let cancelled = false;
      let timer: ReturnType<typeof setInterval> | undefined;

      api.get(/invites/).then(res => {
        if (cancelled) return;
        if (res.data.deadline) {
          const raw = String(res.data.deadline).replace(/(\\+00:00)?Z?$/, "Z");
          const deadline = Date.parse(raw);
          if (Number.isNaN(deadline)) return;

          if (deadline - Date.now() <= 0) {
             setTimeLeft(0);
             return; // Already expired, do not auto-submit on load
          }

          const tick = () => {
            const left = Math.floor((deadline - Date.now()) / 1000);
            setTimeLeft(Math.max(left, 0));
            if (left <= 0) { 
               if (timer) clearInterval(timer);
               submitFnRef.current(); 
            }
          };
          tick();
          timer = setInterval(tick, 1000);
        }
      }).catch(() => {'''
code = re.sub(old_timer, new_timer, code, flags=re.DOTALL)

# Add submitFnRef assignment and correct useEffect cleanup
code = code.replace('submitFnRef.current = executeSubmit;', '') # clean if exists
code = code.replace(
    '    const executeSubmit = async () => {',
    '    submitFnRef.current = executeSubmit;\n\n    const executeSubmit = async () => {'
)

code = re.sub(r'navigate\(/login/\$\{questionId \|\| ""\}.*?\}\);', 'navigate(/login/, { replace: true });\n      });\n      return () => {\n        cancelled = true;\n        if (timer) clearInterval(timer);\n      };\n', code, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched CandidateTestPage')
