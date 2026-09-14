FROM python:3.13.15-slim

WORKDIR /app


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
#строчка внизу запускает приложуху, я у себя накатал небольшой сервак на unicorn для
#проверки бд, а так жду отдел питона, чтобы добавить сюда что надо
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
