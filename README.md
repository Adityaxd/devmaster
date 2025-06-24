# DevMaster

An AI-powered full-stack development platform that enables rapid, production-grade application development through intelligent code generation and multi-agent orchestration.

## 🚀 Overview

DevMaster provides a complete, opinionated ecosystem with powerful simplifying assumptions, platform primitives, and automated helpers that enable developers to build and deploy applications with extreme agility.

## 🎯 Philosophy

- **Convention over Configuration**: Sensible defaults for the entire stack
- **Code Generation over Boilerplate**: Generate high-quality, production-ready code from high-level definitions
- **Full-Stack Integration**: Type-safe integration between backend and frontend
- **Developer Experience First**: Intuitive and efficient development environment

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18+ with TypeScript & Vite
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Styling**: Tailwind CSS with shadcn/ui
- **Agent Orchestration**: LangGraph patterns
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Migrations**: Alembic

## 📊 Project Status

### Phase 1: Foundation & Core Infrastructure ✅ COMPLETE
- Core agent orchestration with LangGraph
- Event-driven architecture
- File system management
- WebSocket support
- LLM integration

### Phase 2: Platform Primitives 🚧 IN PROGRESS
- ✅ **Week 5**: Python-to-SQL Generator (COMPLETE)
- 🎯 **Week 6**: Business Logic-to-API Generator (Next)
- 📅 **Week 7**: FastAPI-to-TypeScript SDK Generator
- 📅 **Week 8**: Integration & Validation

### Phase 3-6: Coming Soon
- Specialist AI agents
- Platform UI
- Advanced features
- Production deployment

## 🏗️ Project Structure

```
devmaster/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── agents/         # AI agent implementations
│   │   ├── core/           # Core infrastructure
│   │   ├── generators/     # Platform Primitives ✨
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routers/        # API endpoints
│   │   └── services/       # Business logic
│   └── tests/              # Test suite
├── frontend/               # React frontend (Phase 4)
├── docs/                   # Project documentation
├── docker-compose.yml      # Local development environment
└── README.md              # This file
```

## 🚦 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend, coming in Phase 4)
- Docker and Docker Compose (optional)
- Git

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/Adityaxd/devmaster.git
cd devmaster
```

2. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the backend:
```bash
uvicorn app.main:app --reload --port 8002
```

5. Access the API:
- API: http://localhost:8002
- API Documentation: http://localhost:8002/docs
- Health Check: http://localhost:8002/health

## 🧪 Testing

Run the test suite:
```bash
cd backend
python -m pytest
```

Run specific test modules:
```bash
# Test the Python-to-SQL generator
python -m pytest tests/generators/test_python_to_sql.py -xvs
```

## 📚 Platform Primitives

### Python-to-SQL Generator ✅

Convert SQLAlchemy models to PostgreSQL DDL:

```python
from app.generators import PythonToSQLGenerator
from app.models.user import User

generator = PythonToSQLGenerator()
sql = generator.generate(User)
```

Try it via API:
```bash
curl -X POST http://localhost:8002/api/v1/generators/python-to-sql \
  -H "Content-Type: application/json" \
  -d '{"model_name": "User"}'
```

## 📖 Documentation

- [System Blueprint](docs/Blueprint.pdf) - What we're building
- [Implementation Plan](docs/Implementation%20Plan.pdf) - Development roadmap
- [Tech Bible](docs/Tech%20Bible.pdf) - How we build
- [Knowledge Base](docs/KnowledgeBase.md) - Technical details
- [Current State](docs/CURRENT_STATE.md) - Project status
- [Progress Report](docs/project_progress_report.md) - Detailed progress

## 🤝 Contributing

This project is currently in active development. Contributions will be welcome once we reach Phase 3.

## 📜 License

[License information to be added]

## 🙏 Acknowledgments

Built with inspiration from modern development platforms and the latest in AI technology.

---

**Current Phase**: Phase 2, Week 5-6 - Building Platform Primitives 🚀
