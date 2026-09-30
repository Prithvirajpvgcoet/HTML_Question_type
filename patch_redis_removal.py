import os

req_path = 'backend/requirements.txt'
with open(req_path, 'r', encoding='utf-8') as f:
    reqs = f.readlines()
with open(req_path, 'w', encoding='utf-8') as f:
    for line in reqs:
        if 'redis' not in line and 'celery' not in line:
            f.write(line)

config_path = 'backend/config.py'
with open(config_path, 'r', encoding='utf-8') as f:
    code = f.read()
# Remove redis_url
code = "\n".join([line for line in code.split('\n') if 'redis_url' not in line])
with open(config_path, 'w', encoding='utf-8') as f:
    f.write(code)

print('Removed Redis!')
