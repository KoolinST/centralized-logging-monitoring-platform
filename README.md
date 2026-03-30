# Internal Developer Platform

[![CI](https://github.com/KoolinST/centralized-logging-monitoring-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/KoolinST/centralized-logging-monitoring-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-blue.svg)](https://postgresql.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-latest-orange.svg)](https://prometheus.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A self-hosted internal developer platform where administrators control access to a full observability stack. Users register via email or Google OAuth, wait for admin approval, and — once approved — get role-based access to live Grafana dashboards, Kibana logs, and Prometheus metrics, all embedded directly in the platform UI.

---

## Features

- **RBAC** — Three roles: `admin`, `developer`, `viewer`. Admins approve or reject registrations and manage user roles from a dedicated panel
- **Admin approval flow** — New users land on a pending page after registration; admins are notified by email and can approve or reject from the admin panel
- **Audit logging** — Every user action (login, logout, registration, approval, role change) is logged to PostgreSQL with IP address and timestamp
- **Authentication** — Email/password with confirmation, Google OAuth, password reset, and session management
- **Observability portal** — Live Grafana panels (CPU, memory, network, disk I/O) embedded directly in the dashboard; links to Kibana and Prometheus
- **Metrics** — 9 custom Prometheus counters and histograms across all auth flows
- **Log aggregation** — Fluentd collects logs from all services and ships them to Elasticsearch; Kibana provides querying and visualization
- **CI/CD** — GitHub Actions pipeline with flake8, black, PostgreSQL service container, and pytest with coverage reporting

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, Flask, SQLAlchemy, PostgreSQL |
| Auth | Flask-Login, Flask-Bcrypt, Authlib (Google OAuth), itsdangerous |
| Metrics | Prometheus, Grafana, Node Exporter |
| Logging | Fluentd, Elasticsearch, Kibana |
| Infrastructure | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest, pytest-cov, factory_boy |
| Code Quality | flake8, black |

---

## User Flow

```
Register (email or Google OAuth)
        │
        V
  Email confirmation
        │
        V
  Pending approval --> Admin notified by email
        │
        V
  Admin approves / rejects
        │
        V
  Approved -> Dashboard with live Grafana panels
  Rejected -> Notified by email
```

---

## Services
 
| Service | Port | Description |
|---|---|---|
| Flask App | 5050 | Main application |
| PostgreSQL | 5432 | Primary database |
| PGAdmin | 8081 | Database GUI (admin only) |
| Prometheus | 9090 | Metrics collection (via `/proxy/prometheus`) |
| Node Exporter | 9100 | Host-level metrics (via `/proxy/node-exporter`) |
| Grafana | 3000 | Metrics dashboards |
| Elasticsearch | 9200 | Log storage and search |
| Kibana | 5601 | Log visualization (via `/proxy/kibana`) |
| Fluentd | — | Log collector |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- A Google Cloud project with OAuth 2.0 credentials (for Google login)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) configured

### 1. Clone the repository

```bash
git clone https://github.com/KoolinST/centralized-logging-monitoring-platform.git
cd centralized-logging-monitoring-platform
```

### 2. Configure environment

```bash
make env
```

Open `.env` and fill in all required values. See [Environment Variables](#environment-variables) below for details.

### 3. Start the stack

```bash
make run
```

This starts all 9 services. On first run Docker will pull images and build the Flask container — this takes a few minutes.

The first admin account is created automatically from your `.env` values (`ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`, `ADMIN_USERNAME`).

### 4. Access the services

| Service | URL |
|---|---|
| Flask App | http://localhost:5050 |
| Admin Panel | http://localhost:5050/admin |
| Grafana | http://localhost:3000 |
| Kibana | http://localhost:5601 |
| Prometheus | http://localhost:9090 |
| PGAdmin | http://localhost:8081 |

---

## Roles & Access
 
| Role | Dashboard | Grafana | Kibana | Prometheus | Admin Panel |
|---|-----------|---|--------|---|---|
| `admin` | Yes | Yes | Yes | Yes | Yes |
| `developer` | Yes | Yes | Yes | Yes | No |
| `viewer` | Yes | Yes | No | No | No |
 
> Kibana, Prometheus, and Node Exporter are proxied through the Flask app at `/proxy/*`.
> Access is enforced server-side, role restrictions apply even if a user guesses the URL directly.

---

## Development

### Install dependencies

```bash
make install
```

### Run tests

```bash
make test          # full suite with coverage
make test-fast     # stop on first failure
```

### Lint and format

```bash
make lint          # flake8
make format        # black
make check         # lint + format check + tests (mirrors CI)
```

### Useful commands

```bash
make logs          # tail logs from all services
make logs-app      # tail logs from flask app only
make shell         # open shell inside flask container
make stop          # stop all services
make clean         # stop services, remove volumes, clear cache
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
make env
```

| Variable | Description                                                                               |
|---|-------------------------------------------------------------------------------------------|
| `SECRET_KEY` | Flask secret key, generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `EMAIL_CONFIRM_SALT` | Salt for email tokens, generate the same way as SECRET_KEY                                |
| `DATABASE_URL` | PostgreSQL connection string                                                              |
| `MAIL_USERNAME` | Gmail address for sending emails                                                          |
| `MAIL_PASSWORD` | Gmail App Password (not your real password)                                               |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID                                                                    |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret                                                                |
| `ADMIN_EMAIL` | Email for the first admin account (auto-created on startup)                               |
| `ADMIN_PASSWORD` | Password for the first admin account                                                      |
| `ADMIN_NAME` | Display name for the first admin                                                          |
| `ADMIN_USERNAME` | Username for the first admin                                                              |

See `.env.example` for the full list.

---

## Project Structure

```
├── app/
│   ├── config/         # Environment configs (dev/prod/testing)
│   ├── forms/          # WTForms form definitions
│   ├── models/         # SQLAlchemy models (User, AuditLog)
│   ├── routes/         # Flask blueprints (auth, dashboard, admin, password)
│   ├── utils/          # Email, token generation, decorators
│   ├── extensions.py   # Flask extension instances
│   └── metrics.py      # Custom Prometheus counters and histograms
├── frontend/
│   ├── static/         # CSS assets
│   └── templates/      # Jinja2 HTML templates
├── monitoring/
│   ├── prometheus.yml       # Prometheus scrape config
│   ├── grafana/             # Grafana configuration
│   └── promtail-config.yaml # Promtail configuration
├── fluentd/
│   └── conf/           # Fluentd pipeline configuration
├── tests/              # Test suite (models, routes, utils)
├── .github/workflows/  # GitHub Actions CI pipeline
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
├── docker-compose.yml  # Full stack orchestration
├── Dockerfile          # Multi-stage production image
├── Makefile            # Developer commands
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development and testing dependencies
```

---

## CI/CD Pipeline

Every push to `main` triggers the GitHub Actions pipeline:

1. **Lint** - flake8 checks for style violations, black checks formatting
2. **Test** - pytest runs the full test suite against a real PostgreSQL container with coverage reporting
3. **Artifacts** - test results, coverage XML, and coverage badge are uploaded as artifacts

The test job only runs if lint passes.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Flask App     │
                    │   :5050         │
                    │  RBAC + Auth    │
                    │  Admin Panel    │
                    │  Audit Logging  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │  PostgreSQL │   │  Prometheus  │   │   Fluentd   │
   │  :5432      │   │  :9090       │   │             │
   │  Users      │   └──────┬───────┘   └──────┬──────┘
   │  Audit Logs │          │                  │
   └─────────────┘   ┌──────▼───────┐   ┌──────▼──────┐
                     │   Grafana    │   │Elasticsearch│
                     │   :3000      │   │  :9200      │
                     └──────────────┘   └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │   Kibana    │
                                        │   :5601     │
                                        └─────────────┘
```

---

## License

MIT