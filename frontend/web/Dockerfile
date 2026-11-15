# Build from the repository root so the image can read the GitHub wiki source:
#   docker build -f frontend/web/Dockerfile -t legacylift-web .
FROM node:24-alpine AS dependencies
WORKDIR /app
COPY frontend/web/package.json frontend/web/package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY frontend/web/ ./
COPY wiki /wiki
ARG NEXT_PUBLIC_NEON_AUTH_URL=""
ENV NEXT_PUBLIC_NEON_AUTH_URL=$NEXT_PUBLIC_NEON_AUTH_URL
ENV API_URL=http://api:8000
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_OUTPUT=standalone
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /wiki /wiki
USER node
EXPOSE 3000
CMD ["node", "server.js"]

