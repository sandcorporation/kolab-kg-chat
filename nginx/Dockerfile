# ── 1단계: React(Vite) 프론트 빌드 ──
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund --loglevel=error
COPY frontend/ ./
RUN npm run build

# ── 2단계: nginx 단일 엔드포인트(정적 SPA + API/SSE 프록시) ──
FROM nginx:alpine
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
