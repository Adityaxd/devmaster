# DevMaster

An AI-powered full-stack development platform that enables rapid, production-grade application development.

## Overview

DevMaster provides a complete, opinionated ecosystem with powerful simplifying assumptions, platform primitives, and automated helpers that enable developers to build and deploy applications with extreme agility.

## Philosophy

- **Convention over Configuration**: Sensible defaults for the entire stack
- **Code Generation over Boilerplate**: Generate high-quality, production-ready code from high-level definitions
- **Full-Stack Integration**: Type-safe integration between backend and frontend
- **Developer Experience First**: Intuitive and efficient development environment

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18+ with TypeScript & Vite
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Styling**: Tailwind CSS with shadcn/ui
- **Agent Orchestration**: LangGraph patterns
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Migrations**: Alembic

## Project Structure

```
devmaster/
├── backend/           # FastAPI backend application
├── frontend/          # React frontend application
├── docs/             # Project documentation
├── docker-compose.yml # Local development environment
└── README.md         # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Adityaxd/devmaster.git
cd devmaster
```

2. Start the development environment:
```bash
docker-compose up
```

3. Access the applications:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development

See the [project documentation](docs/) for detailed development guidelines and architectural decisions.

## License

[License information to be added]