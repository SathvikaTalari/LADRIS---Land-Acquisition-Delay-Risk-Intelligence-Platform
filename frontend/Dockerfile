FROM node:20-slim

WORKDIR /app

# Copy package definition files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite dev server accessible externally
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
