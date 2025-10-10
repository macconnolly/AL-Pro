set shell := ["/bin/bash", "-cu"]

[aliases]
b = bootstrap
t = test
l = lint

bootstrap:
poetry install --with dev
poetry run python scripts/prepare_fixtures.py

lint:
poetry run ruff check .
poetry run black --check .
poetry run isort --check-only .
poetry run mypy

format:
poetry run black .
poetry run isort .

ha-validate:
poetry run hassfest --integration-path custom_components/al_layer_manager
poetry run hacs validate

test:
poetry run pytest

scenario name="morning":
poetry run pytest tests/test_scenarios.py -k morning
