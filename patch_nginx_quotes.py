import os

files_to_patch = [
    'frontend-admin/Dockerfile',
    'frontend-candidate/Dockerfile'
]

for file_path in files_to_patch:
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Fix the quoting issue so  gets evaluated by the shell
    bad_cmd = "CMD sh -c \"sed -i 's/listen 80;/listen ;/g' /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'\""
    good_cmd = "CMD sh -c \"sed -i \\\"s/listen 80;/listen \\;/g\\\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'\""
    
    code = code.replace(bad_cmd, good_cmd)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

print('Patched Nginx config quotes')
