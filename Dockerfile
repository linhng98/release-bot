FROM python:3.10.6-alpine3.16

WORKDIR app

RUN apk add --no-cache make build-base git libgit2-dev
COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8080
CMD ["uvicorn", "main:app", "--port", "8080"]