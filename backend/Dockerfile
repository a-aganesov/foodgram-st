FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && pip list

COPY . .

CMD ["gunicorn", "foodgram.wsgi:application", "-b", "0.0.0.0:8000"]

