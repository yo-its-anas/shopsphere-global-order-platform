FROM node:20-alpine AS build

WORKDIR /app

# Vite embeds these public endpoints at build time. They must never contain secrets.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_KEYCLOAK_URL=http://localhost:8081
ARG VITE_KEYCLOAK_REALM=shopsphere
ARG VITE_KEYCLOAK_CLIENT_ID=shopsphere-frontend
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL} \
    VITE_KEYCLOAK_REALM=${VITE_KEYCLOAK_REALM} \
    VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER 101:101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1:8080/health"]

CMD ["nginx", "-g", "daemon off;"]
