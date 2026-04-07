# Contributing to ABrain

We want to make contributing to ABrain as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `develop`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Pull Request Process

1. Update the README.md with details of changes to the interface, if applicable
2. Update the docs with any new features or changes
3. The PR will be merged once you have the sign-off of two other developers
4. Make sure the CI pipeline passes

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issue tracker](https://github.com/EcoSphereNetwork/Agent-NN/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/EcoSphereNetwork/Agent-NN/issues/new).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/EcoSphereNetwork/Agent-NN.git
cd Agent-NN
```

2. Install dependencies:
```bash
poetry install
```

3. Set up pre-commit hooks:
```bash
poetry run pre-commit install
```

4. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

## Code Style

We use several tools to maintain code quality:

- `black` for code formatting
- `isort` for import sorting
- `flake8` for style guide enforcement
- `mypy` for type checking

Run the full suite:
```bash
poetry run black .
poetry run isort .
poetry run flake8 .
poetry run mypy .
```

## Testing

We use `pytest` for testing. Run the tests:
```bash
poetry run pytest
```

With coverage:
```bash
poetry run pytest --cov=. --cov-report=xml
```

## Documentation

We use `mkdocs` with the Material theme for documentation. To serve docs locally:
```bash
poetry run mkdocs serve
```

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
