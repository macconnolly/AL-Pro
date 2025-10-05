# Contributing to AL Layer Manager

Welcome to the adaptive lighting lab. This guide documents the workflows enforced by CI and our local developer experience.

## Branch Strategy
- `main`: Always releasable. Protected by required reviews, status checks, and end-to-end scenario validation.
- `develop`: Integration branch for beta features. Feature branches fork from and merge back into `develop` via pull requests.

All pull requests must:
1. Pass lint (`ruff`), style (`black`), type (`mypy`), and unit tests (`pytest`).
2. Provide updated documentation and task tracker entries for every change.
3. Include scenario test coverage or rationale when not applicable.

## Local Development
1. Install [Poetry](https://python-poetry.org/).
2. Run `poetry install --with dev` to install dependencies.
3. Use `just bootstrap` (see `justfile`) to apply pre-commit hooks and prepare fixtures.
4. Execute `just test` before every commit.

## Continuous Integration
GitHub Actions enforce the following workflows:
- `ci-lint.yml`: black, ruff, isort, yamllint.
- `ci-type.yml`: mypy static typing.
- `ci-test.yml`: pytest with coverage ≥80% overall, ≥90% in manager modules.
- `ci-ha.yml`: hassfest + hacs validation to ensure Home Assistant compliance.

Pull requests failing any workflow cannot be merged. Reviewers expect screenshots or logs for UX or automation changes.
