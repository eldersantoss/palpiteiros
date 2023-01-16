FROM python:3.11-slim

EXPOSE 8000

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/requirements.txt
# && useradd -U app_user \
# && install -d -m 0755 -o app_user -g app_user /app/static

WORKDIR /
# USER app_user:app_user
# COPY --chown=app_user:app_user . .
COPY . .
RUN chmod +x scripts/*.sh

ENTRYPOINT [ "./scripts/entrypoint.sh" ]
CMD [ "./scripts/start.sh", "server" ]
EXPOSE 8000