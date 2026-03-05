# MEC Cupos Checker

Automated web scraper for monitoring appointment availability on the Uruguayan Ministry of Education (MEC) website and
sending Telegram notifications when slots become available.

## Overview

This project automates the process of checking for available appointment slots on https://bpmgob.mec.gub.uy. It uses
browser automation to navigate the website, solves security questions using AI, intercepts network requests to extract
availability data, and sends notifications via Telegram when new appointments are found.

## Features

- **Automated Login** - Handles authentication flow with session persistence
- **AI-Powered Captcha Solving** - Uses Groq AI (LLaMA 3.3) to solve security questions
- **Network Interception** - Extracts data directly from API responses
- **Smart Notifications** - Only notifies when new dates appear (prevents duplicate alerts)
- **Multiple Trámites Support** - Can check multiple appointment types in a single run
- **Dockerized Deployment** - Runs in a container with scheduled cron execution
- **Headless Operation** - Runs without GUI for server deployment

## Architecture

### Components

- **main.py** - Entry point that orchestrates the checking process
- **mec_checker.py** - Core scraper using Playwright for browser automation
- **ai_agent.py** - Groq AI integration for solving security questions
- **notifier.py** - Telegram notification sender
- **utils.py** - State management (loads/saves last notified date)

### How It Works

1. Launches headless Chromium browser using Playwright
2. Loads saved session state (if available) to skip login
3. Navigates to MEC website and verifies authentication
4. For each configured etapa (appointment type):
    - Navigates to the appointment page
    - Solves security question using AI
    - Intercepts API responses to extract available dates
5. Compares findings with last notification state
6. Sends Telegram notification if new dates are found
7. Saves state to prevent duplicate notifications

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (for containerized deployment)
- Telegram Bot Token and Chat ID
- Groq API Key (for AI captcha solving)
- Valid MEC account credentials

## Installation

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd mec_cupos_checker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create json files for state management
echo "{}" > available.json
echo "{}" > storage_state.json
```

### Docker Deployment

```bash
# Build the image
docker compose build

# Run the container
docker compose up -d
```

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
# MEC Website Credentials
MEC_USER=your_passport_or_document_number
MEC_PASSWORD=your_password

# Etapas (Appointment Types) - Comma-separated IDs
ETAPAS_IDS=123,456,789

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHATBOT_IDS=your_chat_id   # Comma-separated for multiple IDs

# Groq AI API Key
GROQ_API_KEY=your_groq_api_key

# Optional: Disable cron (run once and exit)
CRON_DISABLED=true

# Execution interval in minutes
CRON_JOB_TIMER_MINUTES=30
```

### Getting Configuration Values

**Telegram Bot Token & Chat ID:**

1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your Chat ID by messaging [@userinfobot](https://t.me/userinfobot)

**Groq API Key:**

1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key in the dashboard

**Etapas IDs:**

- Navigate to the MEC website and inspect the URLs when selecting appointment types
- The etapa ID appears in URLs like: `https://bpmgob.mec.gub.uy/etapas/ejecutar/{ETAPA_ID}/0`

## Usage

### Run Locally (One-Time Check)

```bash
# Ensure .env is configured
python main.py
```

### Run with Docker (Scheduled Checks)

This project includes an `entrypoint.sh` that sets up a cron job that runs `python main.py` every 30 minutes
(expression `*/30 * * * *`).

How it works:

- `Dockerfile` installs `cron` and copies `entrypoint.sh`.
- `entrypoint.sh` generates `/etc/envcron` with environment variables (read from `/app/.env` if it exists, or from the
  container environment) and registers a `crontab` that executes `python main.py` every 30 minutes, redirecting logs to
  `/var/log/mec_cupos_checker.log`.
- The container starts `cron` in the foreground so Docker keeps it alive.

The Docker container runs the checker every 30 minutes automatically:

```bash
# Start the service
docker compose up -d

# View logs
docker compose logs -f app

# Verify that the cron job has the correct path
docker exec mec_checker crontab -l

# Verify the exported environment variables
docker exec mec_checker cat /etc/envcron

# View detailed execution logs
docker exec mec_checker tail -f /var/log/mec_cupos_checker.log

# Stop the service
docker compose down
```

Notes:

- If you need to change the frequency, modify the `CRON_JOB` variable inside `entrypoint.sh`.
- In production environments you can also schedule using host cron/systemd timer instead of using cron inside the
  container.

### Run Once in Docker (Debugging)

```bash
# Set CRON_DISABLED=true in .env, then:
docker compose up --build
```

## Project Structure

```
mec_cupos_checker/
├── main.py                 # Entry point
├── mec_checker.py          # Main scraper logic
├── ai_agent.py             # AI integration
├── notifier.py             # Telegram notifications
├── utils.py                # State management
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Docker orchestration
├── entrypoint.sh           # Container startup script
├── mec_chain.pem           # SSL certificate chain
├── README_CRON.md          # Cron documentation
├── available.json          # State file (auto-generated)
└── storage_state.json      # Browser session (auto-generated)
```

## Pending Improvements

### High Priority

1. **Fix Data Accumulation Bug** - Reset datos between etapa checks
2. **Add Comprehensive Error Handling**
    - Validate all environment variables on startup
    - Wrap AI agent calls in try-except
    - Handle notification failures gracefully
    - Add global exception handler in main.py
3. **Replace Infinite Timeouts** - Use bounded timeouts everywhere
4. **Add Failure Alerting** - Send Telegram notification when scraper fails
5. **Implement Robust Wait Strategies** - Replace fixed 2-second waits with event-based waits

### Medium Priority

6. **Add Health Check Endpoint** - Monitor scraper status
7. **Implement Retry Logic** - For navigation, API calls, and notifications
8. **Atomic State Writes** - Use temp file + rename to prevent corruption
9. **Selector Validation** - Check element existence before interaction
10. **Add Logging Improvements**
    - Structured JSON logging
    - Separate log levels for different severity
    - Include execution metrics (duration, success rate)

### Low Priority

11. **Add Type Hints** - Complete type annotations throughout
12. **Create Test Suite** - Unit and integration tests
13. **Make Cron Schedule Configurable** - Via environment variable
14. **Add Multiple Notification Channels** - Email, SMS, webhooks
15. **Create Web Dashboard** - View check history and status
16. **Implement Rate Limiting** - Avoid triggering anti-bot measures
17. **Add CI/CD Pipeline** - Automated testing and deployment

### Code Quality

18. **Extract Magic Numbers** - Move timeouts to configuration
19. **Standardize Language** - Either Spanish or English consistently
20. **Add Documentation** - Docstrings for all functions
21. **Improve Error Messages** - More descriptive logging

## Security Notes

- The `mec_chain.pem` certificate file is included for SSL/TLS verification with the MEC website
- Credentials are loaded from environment variables (never commit `.env` file)
- Session state is persisted locally - secure the `storage_state.json` file
- Groq API key should be kept secret and rotated periodically

## Troubleshooting

### Scraper hangs indefinitely

- Check for infinite timeouts in logs
- Verify network connectivity to MEC website
- Ensure Playwright browser is properly installed

### Login fails repeatedly

- Verify MEC_USER and MEC_PASSWORD are correct
- Delete `storage_state.json` to force fresh login
- Check if MEC website changed authentication flow

### No notifications received

- Verify Telegram bot token and chat ID
- Check if dates are actually new (check `available.json`)
- Look for errors in logs: `docker exec mec_checker tail -f /var/log/mec_cupos_checker.log`

### AI agent fails to solve security question

- Verify GROQ_API_KEY is set correctly
- Check Groq API quotas and rate limits
- Review question format in logs

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Fix bugs or implement improvements from the pending list
4. Submit a pull request

## License

[Add your license information here]

## Disclaimer

This tool is for personal use only. Ensure compliance with the MEC website's terms of service. The authors are not
responsible for any misuse or violations.
