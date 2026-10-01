#!/bin/sh
# Replace the port in nginx config with the PORT env var (default 80)
PORT=${PORT:-80}
cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen ${PORT};
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
echo "Starting nginx on port ${PORT}"
exec nginx -g "daemon off;"
