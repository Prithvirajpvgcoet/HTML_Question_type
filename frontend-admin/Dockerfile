FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ARG VITE_CANDIDATE_URL
ENV VITE_CANDIDATE_URL=$VITE_CANDIDATE_URL
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:22-alpine
RUN npm install -g serve
WORKDIR /app
COPY --from=build /app/dist ./dist
CMD sh -c "serve -s dist -l tcp://0.0.0.0:${PORT:-3000}"
