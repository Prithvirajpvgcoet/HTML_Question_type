import re

with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<th className="p-4 font-medium w-10">#</th>', '<th className="p-4 font-medium w-10">#</th>\\n                  <th className="p-4 font-medium">Status</th>')

row_cell = '''<td className="p-4 align-top">
                    <span className={\px-2 py-1 text-xs font-medium rounded-full \\}>
                      {a.last_validation_status === 'passed' ? '✅ Passed' : a.last_validation_status === 'failed' ? '❌ Failed' : 'Pending'}
                    </span>
                  </td>'''

text = text.replace('<td className="p-4 text-gray-500 align-top">{index + 1}</td>', '<td className="p-4 text-gray-500 align-top">{index + 1}</td>\\n                  ' + row_cell)

with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
