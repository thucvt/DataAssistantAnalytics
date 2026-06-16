FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Dev server (Phase 1). Production có thể đổi sang build + nginx serve tĩnh.
CMD ["npm", "run", "dev"]
