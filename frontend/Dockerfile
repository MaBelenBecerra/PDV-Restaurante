# Step 1: Build the React application with Vite
FROM node:22-alpine AS build
WORKDIR /app

# Declare build arguments for Vite compile-time environment variables
ARG VITE_INVENTORY_API_URL
ARG VITE_PURCHASE_API_URL
ARG VITE_SALE_API_URL

# Set them as environment variables so npm run build can access them
ENV VITE_INVENTORY_API_URL=$VITE_INVENTORY_API_URL
ENV VITE_PURCHASE_API_URL=$VITE_PURCHASE_API_URL
ENV VITE_SALE_API_URL=$VITE_SALE_API_URL

# Copy dependency configuration files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application files
COPY . .

# Build the application
RUN npm run build

# Step 2: Serve the build output using Nginx
FROM nginx:stable-alpine

# Generate the custom nginx configuration for SPA routing inline
RUN printf 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    location / {\n\
    root /usr/share/nginx/html;\n\
    index index.html index.htm;\n\
    try_files $uri $uri/ /index.html;\n\
    }\n\
    error_page 500 502 503 504 /50x.html;\n\
    location = /50x.html {\n\
    root /usr/share/nginx/html;\n\
    }\n\
    }\n' > /etc/nginx/conf.d/default.conf

# Copy build files from the build stage to Nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
