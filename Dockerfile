FROM python:3.10.6-alpine3.16

WORKDIR app

RUN apk add --no-cache make build-base git libgit2-dev
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
