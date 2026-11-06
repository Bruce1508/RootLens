FROM node:22.23.4-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN mkdir -p .next && chown -R node:node /app

USER node

EXPOSE 3000

CMD ["npm", "run", "dev"]
