FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ARG VITE_CANDIDATE_URL
ENV VITE_CANDIDATE_URL=$VITE_CANDIDATE_URL
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Inject basic SPA routing config for Nginx
RUN echo "server { listen 80; location / { root /usr/share/nginx/html; index index.html index.htm; try_files $uri $uri/ /index.html; } }" > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
