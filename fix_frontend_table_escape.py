import re

with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the bad backtick escape which caused \p instead of 
text = text.replace(r'<span className={\px-2', '<span className={px-2')
text = text.replace(r'text-gray-600}\}>', r'text-gray-600}}>')

with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
