# Використовуємо офіційний Node.js образ
FROM node:20-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо package.json і package-lock.json
COPY package*.json ./

# Встановлюємо залежності
RUN npm install

# Копіюємо весь код
COPY . .

# Відкриваємо порт
EXPOSE 5173

# Стартуємо dev сервер Vite
CMD ["npm", "run", "dev", "--", "--host"]
