# Dockerfile for WithOps DevSecOps Frontend (SvelteKit + Node adapter)

# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Build arguments for Vite environment variables
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_BASE_URL=http://localhost:9100
ARG VITE_AUTH0_DOMAIN=dev-sabxychpf6paj41u.us.auth0.com
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_CALLBACK_URL
ARG VITE_AUTH0_AUDIENCE=https://api.withops.com

# Set as environment variables for the build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL
ENV VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN
ENV VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID
ENV VITE_AUTH0_CALLBACK_URL=$VITE_AUTH0_CALLBACK_URL
ENV VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy source code
COPY frontend/ .

# Build the SvelteKit app with environment variables baked in
RUN npm run build

# Production stage (Node.js server)
FROM node:20-alpine AS prod
WORKDIR /app
COPY --from=build /app/package.json ./
COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules

EXPOSE 3000
CMD ["node", "build"]
