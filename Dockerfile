FROM node:24 
WORKDIR /usr/local/app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5000

CMD ["npx", "nodemon" "server.js"]
