FROM nginx:stable-alpine

# Копіюємо свій nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Копіюємо фронт
COPY index.html                /usr/share/nginx/html/index.html
COPY static                   /usr/share/nginx/html/static

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
