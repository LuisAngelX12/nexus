# NEXUS

[![NEXUS CI](https://github.com/LuisAngelX12/NEXUS/actions/workflows/ci.yml/badge.svg)](https://github.com/LuisAngelX12/NEXUS/actions/workflows/ci.yml)

Privacy-first intelligent document management and analysis platform.

> 🚧 NEXUS is currently under active development.

## Overview

NEXUS is a Python-based platform designed to help users organize, analyze, search and protect their documents while keeping privacy as a core principle.

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker
- Pytest
- Ruff
- MyPy

## Development

### Requirements

- Python 3.13+
- Docker
- Git

### Run the API

```bash
uvicorn backend.app.main:app --reload
```

## Running with Docker

### Requirements

- Docker
- Docker Compose

### Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

In Windows PowerShell, you can also specify:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables.

### Start NEXUS

```bash
docker compose up --build
```

## API

### Open:

http://localhost:8000/docs

### Stop:

```bash
docker compose down
```