# Contribution Guidelines

Thank you for considering contributing to the CTR Toolkit!

## How to Contribute

- **Report bugs** – Use the issue tracker (Bug Report template).
- **Suggest features** – Use the Feature Request template.
- **Submit code** – Open a pull request with a clear description of your changes.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use 4 spaces for indentation (no tabs).
- Keep line length ≤ 99 characters (or ≤ 120 if readability suffers).
- Use descriptive variable and function names.
- Add docstrings for new functions and classes (Google style preferred).

## Commit Messages

- Use the imperative mood (“Add feature” not “Added feature”).
- Keep the subject line under 72 characters.
- Reference issues when applicable (e.g., `Fixes #123`).

## Pull Request Process

1. Fork the repository and create a branch from `develop`.
2. Make your changes, add tests if possible.
3. Run the test suite locally (see `testing.md`).
4. Submit the PR against the `develop` branch.
5. Wait for the CI checks to pass and a maintainer to review.

## Development Setup

- Blender 3.3 or newer.
- Python 3.11+ for standalone scripts.
- For local testing, set up `blender_execs.txt` as described in `testing.md`.

## License

By contributing, you agree that your contributions will be licensed under the same GPL-2.0 license as the project.
