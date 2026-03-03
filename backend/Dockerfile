FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc cron && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Setup cron
COPY crontab /etc/cron.d/finassist-cron
RUN chmod 0644 /etc/cron.d/finassist-cron
RUN crontab /etc/cron.d/finassist-cron
RUN touch /var/log/cron.log

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
