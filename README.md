# BlueGuard - AI Ocean Intelligence Platform

A production-ready MVP for marine protection monitoring using AI-powered pollution detection, illegal fishing tracking, and ocean health prediction.

## Features

- **Real-time Vessel Tracking**: Monitor vessel movements with AIS data integration
- **Pollution Detection**: AI-powered detection using YOLOv8 on satellite imagery
- **Route Prediction**: LSTM-based prediction of vessel trajectories
- **Ocean Health Forecasting**: Prophet-based forecasting of Ocean Health Index
- **Interactive Map**: Real-time visualization of marine data with layer controls
- **Alert System**: Automated alerts for high-risk events

## Tech Stack

- **Frontend**: React + Vite + Tailwind CSS + React-Leaflet
- **Backend**: FastAPI + SQLModel + PostgreSQL/PostGIS
- **AI/ML**: YOLOv8, PyTorch LSTM, Prophet
- **Infrastructure**: Docker Compose, Redis, Celery

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run: `docker-compose up --build`
4. Access:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Initial Setup

Run migrations:
```bash
docker-compose exec backend alembic upgrade head
```

Load initial MPA data:
```bash
docker-compose exec backend python scripts/load_mpas.py
```

## Development

- Backend hot-reload enabled
- Frontend hot-reload enabled
- Access PostgreSQL: `psql -h localhost -U blueguard -d blueguard_db`

## License

MIT
