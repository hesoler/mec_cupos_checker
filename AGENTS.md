# AGENTS.md - Coding Guidelines for MEC Cupos Checker

This file contains coding guidelines, build commands, and conventions for the MEC Cupos Checker project. Follow these
guidelines when contributing code changes.

## Project Overview

MEC Cupos Checker is a Python application that automates checking for appointment availability on the Uruguayan Ministry
of Education website using browser automation with Playwright, AI-powered captcha solving, and Telegram notifications.

## Build, Lint, and Test Commands

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Running the Application

```bash
# Run once locally
python src/main.py

# Run with Docker (scheduled execution)
scripts compose -f scripts/scripts-compose.yml up -d

# Run once in Docker (for debugging)
# CRON_DISABLED=true
scripts compose -f scripts/scripts-compose.yml up --build
```

### Testing

Currently, no formal test suite exists. Run the application manually to verify functionality:

```bash
# Basic functionality test
python src/main.py

# Check logs in Docker
scripts compose -f scripts/scripts-compose.yml logs -f app
```

### Code Quality Tools

No linting tools are currently configured. Consider adding:

- `ruff` for linting and formatting
- `mypy` for type checking
- `pytest` for testing framework

## Code Style Guidelines

### Python Version

- Target: Python 3.12+
- Ensure compatibility with the Docker base image (python:3.12-slim)

### Import Organization

```python
# Standard library imports
import logging
import os
import time

# Third-party imports (alphabetical)
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Error as PlaywrightError

# Local imports (alphabetical)
from ai_agent import consultar_agente_ia_groq
from notifier import send_telegram
from utils import cargar_estado, guardar_estado
```

### Naming Conventions

#### Variables and Functions

- Use `snake_case` for variables, functions, and methods
- Examples: `cargar_estado()`, `send_telegram()`, `etapa_id`

#### Classes

- Use `PascalCase` for class names
- Examples: `MECChecker`, `TelegramNotifier`

#### Constants

- Use `UPPER_CASE` for constants
- Examples: `STATE_FILE`, `TIMEOUT_DEFAULT`

### Type Hints

- Use type hints for function parameters and return values
- Examples:

```python
def check_tramite(self, etapa_id: int) -> dict:


    def esta_logueado(self) -> bool:


    def __init__(self, headless: bool = True):
```

### Documentation

- Add docstrings for complex functions and classes
- Keep docstrings concise but informative
- Example:

```python
def _safe_goto(self, url: str, wait_until: str = "networkidle", timeout: int = 30000, retries: int = 3,
               backoff: float = 1.5):
    """
    Navigate to a URL with retries when Playwright throws TimeoutError or other transient errors.
    """
```

### Logging

- Use the standard `logging` module configured in `mec_checker.py`
- Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- Include relevant context in log messages
- Use emojis sparingly for visual clarity in INFO logs
- Examples:

```python
logging.info("🔎 Verificando sesión...")
logging.error(f"Error al consultar agente IA: {e}")
logging.warning("Timeout esperando redirección a iduruguay; continuando de todos modos")
```

### Error Handling

- Use try-except blocks for operations that may fail
- Log errors with context
- Re-raise exceptions after logging unless handled gracefully
- Validate inputs and environment variables early
- Example:

```python
try:
    client = Groq()
    # ... API call
except Exception as e:
    logging.error(f"Error al consultar agente IA: {e}")
    raise
```

### Code Structure

#### Class Organization

- Group methods by functionality with comment separators
- Example:

```python
# -------------------------
# Lifecycle methods
# -------------------------
def start(self):


    def close(self):


# -------------------------
# Authentication
# -------------------------
def ensure_login(self):


    def esta_logueado(self):
```

#### Function Length

- Keep functions focused and under 50 lines when possible
- Extract complex logic into helper methods
- Example: `_safe_goto()` handles retry logic separately from `ensure_login()`

### Security Best Practices

- Never log sensitive information (passwords, API keys, tokens)
- Load credentials from environment variables only
- Validate SSL certificates (mec_chain.pem is included in `config/` for MEC website)
- Store session state securely (`data/storage_state.json`)
- Rotate API keys periodically

### File Organization

- One class per file when possible
- Utility functions in dedicated modules
- Keep related functionality together
- Current structure (in `src/`):
    - `main.py`: Entry point and orchestration
    - `mec_checker.py`: Core scraping logic
    - `ai_agent.py`: AI integration
    - `notifier.py`: Notification sending
    - `utils.py`: State management utilities

### Configuration

- Use environment variables for all configuration
- Validate required variables on startup
- Document all environment variables in README.md
- Example validation:

```python
required_vars = ["MEC_USER", "MEC_PASSWORD", "ETAPAS_IDS", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GROQ_API_KEY"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
```

### Browser Automation Best Practices

- Use explicit waits instead of fixed timeouts when possible
- Handle network errors gracefully with retries
- Clean up browser resources properly
- Use headless mode for production
- Example:

```python
# Prefer event-based waits
self.page.wait_for_selector("div.controls > input[type='text']~label", timeout=2000)

# Use bounded timeouts instead of infinite waits
self.page.wait_for_url("**bpmgob.mec.gub.uy/**", timeout=120000)
```

### State Management

- Use JSON files for persistent state
- Handle file corruption gracefully
- Implement atomic writes (consider temp file + rename)
- Current implementation in `utils.py`

### Docker Best Practices

- Use multi-stage builds if needed for optimization
- Include only necessary system dependencies
- Mount volumes for persistent data (`data/available.json`, `data/storage_state.json`)
- Use environment files for configuration
- Keep container stateless except for mounted volumes

### Performance Considerations

- Minimize browser interactions
- Use network interception instead of DOM parsing when possible
- Cache session state to avoid repeated logins
- Implement rate limiting to avoid anti-bot measures

## Language Consistency

The codebase currently mixes Spanish and English:

- Spanish: Comments, variable names (`etapa_id`, `tramite`), log messages
- English: Function names (`send_telegram`, `cargar_estado`), class names (`MECChecker`)

**Recommendation**: Standardize on English for all new code to improve maintainability and accessibility for
international contributors.

## Development Workflow

1. Create feature branch from main
2. Implement changes following these guidelines
3. Test locally: `python src/main.py`
4. Test in Docker: `docker compose -f docker/docker-compose.yml up --build`
5. Commit with descriptive messages
6. Create pull request

## Future Improvements

### High Priority

- Add comprehensive error handling and validation
- Implement proper testing framework (pytest)
- Add linting and formatting tools (ruff, black)
- Replace fixed timeouts with robust wait strategies
- Add health check endpoint

### Medium Priority

- Complete type hints throughout codebase
- Implement structured logging (JSON format)
- Add retry logic for all external operations
- Create comprehensive test suite
- Add CI/CD pipeline

### Low Priority

- Make cron schedule configurable
- Add multiple notification channels
- Create web dashboard
- Implement rate limiting
- Add performance monitoring

## Contributing

When contributing:

1. Follow these guidelines
2. Add tests for new functionality
3. Update documentation (README.md, this file)
4. Ensure Docker deployment works
5. Test both local and containerized execution

## Emergency Contacts

If the scraper breaks due to website changes:

- Check MEC website for authentication flow changes
- Delete `data/storage_state.json` to force fresh login
- Review network logs for API endpoint changes
- Update selectors if DOM structure changed</content>
  <parameter name="filePath">AGENTS.md
