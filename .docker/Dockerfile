FROM python:3.10

WORKDIR /code

COPY pyproject.toml poetry.lock ./

RUN pip install poetry==2.0.1 && poetry install --only main --no-root --no-directory

COPY . .

RUN poetry install --only main

CMD ["poetry", "run", "fastapi", "dev", "plc_platform_backend/main.py", "--port", "8000", "--host", "0.0.0.0"]
