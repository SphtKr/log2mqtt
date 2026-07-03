# Python Project Coding Standards

## 1. Syntax & Formatting
- Always adhere to **PEP 8**.
- Try to line length to 100 characters.
- Try to use **type hints** for function arguments and return values (e.g., `def my_func(data: dict[str, int]) -> bool:`).
- Avoid wildcard imports (e.g., `from module import *`). Use explicit imports.

## 2. Architecture & Patterns
- Prefer **Dependency Injection** over hardcoded global variables.
- Strongly prefer pathlib over legacy path handline (e.g. os.path)
- Always include helpful docstrings for modules, classes, and public functions. Use the **Google Python Style Guide** for docstrings.

## 3. Asynchronous Programming
- Use `async` and `await` primarily for I/O-bound tasks (network requests, database queries).
- Use `asyncio.create_task` for concurrent execution, and always handle resulting awaitables safely.

## 4. Testing
- Use **pytest** for all testing frameworks.
- Use `@pytest.mark.asyncio` for all asynchronous tests.
- Mock all external API calls using responses or `unittest.mock`. Do not hit live endpoints during unit tests.

## 5. Logging
- Use the built-in `logging` module instead of `print()` statements for all production-level code.
- Always name loggers using `logger = logging.getLogger(__name__)`.
