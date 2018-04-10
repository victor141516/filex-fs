FROM python:3.6-alpine3.7

RUN apk add --no-cache postgresql-dev gcc musl-dev
COPY filex-fx /app
WORKDIR /app
RUN pip install -r requirements.txt

CMD [ "gunicorn", "-w4", "-b :8000", "main:app" ]
