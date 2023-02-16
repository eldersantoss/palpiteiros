FROM python:3.11

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -U pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000
