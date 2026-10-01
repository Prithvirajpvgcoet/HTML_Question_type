FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:22-alpine
RUN npm install -g serve
COPY --from=build /app/dist /app/dist
CMD sh -c "serve -s /app/dist -l tcp://0.0.0.0:${PORT:-3000}"
