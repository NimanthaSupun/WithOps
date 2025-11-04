# Dockerfile for WithOps DevSecOps Frontend (SvelteKit + Node adapter)

# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy source code
COPY frontend/ .

# Build the SvelteKit app
RUN npm run build

# Production stage (Node.js server)
FROM node:20-alpine AS prod
WORKDIR /app
COPY --from=build /app/package.json ./
COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules

EXPOSE 3000
CMD ["node", "build"]
