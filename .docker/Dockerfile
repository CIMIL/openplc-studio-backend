FROM python:3.10

WORKDIR /code

COPY pyproject.toml poetry.lock ./

RUN pip install poetry==2.0.1 && poetry install --only main --no-root --no-directory

COPY . .

RUN poetry install --with dev

CMD ["poetry", "run", "python3", "-m", "debugpy", "--listen", "0.0.0.0:5678", "plc_platform_backend/debug.py"]
