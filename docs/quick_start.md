# Quick Start Guide

## Running Without Docker (Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (running on port 5433)
- Redis (running on port 6379)

### Backend Setup

1. Create a Python virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the backend server:
```bash
python run_dev.py
```

The API will be available at http://localhost:8000
API Documentation: http://localhost:8000/api/docs

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:5173

## Running With Docker (Recommended)

1. Start all services:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f
```

3. Stop services:
```bash
docker-compose down
```

## Testing the Setup

### Backend Health Check
```bash
curl http://localhost:8000/health
```

### Full System Health Check
```bash
curl http://localhost:8000/api/v1/health/full
```

## Common Issues

1. **Port Conflicts**: If PostgreSQL is already running on port 5432, we use port 5433 instead.

2. **Database Connection**: Ensure PostgreSQL is running and the credentials in `.env` match your setup.

3. **Redis Connection**: Ensure Redis is running on port 6379.

## Next Steps

- Create database models
- Implement authentication
- Set up LangGraph orchestration
- Build agent infrastructure
