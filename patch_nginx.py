import os

files_to_patch = [
    'frontend-admin/Dockerfile',
    'frontend-candidate/Dockerfile'
]

for file_path in files_to_patch:
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Change the CMD to replace port 80 with  dynamically
    if 'CMD ["nginx", "-g", "daemon off;"]' in code:
        code = code.replace('CMD ["nginx", "-g", "daemon off;"]', 'CMD sed -i -e "s/listen 80;/listen ;/g" /etc/nginx/conf.d/default.conf && nginx -g "daemon off;"')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

print('Patched Nginx config to use dynamic PORT')
