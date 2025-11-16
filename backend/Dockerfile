FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY inventree-part-import ./inventree-part-import
COPY inventree_part_import_config ./inventree_part_import_config
RUN pip install --no-cache-dir -e ./inventree-part-import

WORKDIR /app/backend
RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]
