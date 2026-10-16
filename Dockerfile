FROM python:3-alpine
WORKDIR /app
COPY . .
EXPOSE 4002
CMD ["sh", "-c", "python -m http.server ${PORT:-4002}"]
