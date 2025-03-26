# Plotter Development Guidelines

## Commands
- Format code: `black .`
- Type check: `mypy .`
- Lint code: `pylint main.py` (for single file) or `pylint src/` (for all source)
- Run application: `python main.py`

## Code Style
- Use Python 3.10+ features, including type hints
- Follow PEP 8 conventions with Black formatter
- Import order: standard library, third-party packages, local modules (group with blank lines)
- Use type annotations for all function parameters and return values
- Docstrings for all classes and functions in triple quotes, with clear descriptions
- Use descriptive variable names in snake_case
- Constants in UPPER_CASE
- Classes in CamelCase
- Handle errors with specific exception types (avoid bare `except`)
- Function calls use parentheses after slot names (connect_signals())
- Use Qt's signal/slot mechanism for inter-component communication

## Architecture
- Maintain separation between core and UI components
- Core components should be in `src/core/`
- UI components should be in `src/ui/`
- Follow PyQt6 patterns for signal/slot connections
- Always clean up resources in closeEvent handlers