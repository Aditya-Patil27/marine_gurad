# BlueGuard 🌊

**AI-Powered Ocean Surveillance & Maritime Intelligence Platform**

BlueGuard is an advanced maritime monitoring system that leverages artificial intelligence, satellite imagery, and real-time vessel tracking to protect marine ecosystems, detect illegal activities, and ensure compliance with environmental regulations.

---

## 🎯 Mission

To safeguard our oceans through intelligent surveillance, predictive analytics, and real-time threat detection—empowering maritime authorities, environmental organizations, and coastal communities with actionable intelligence.

---

## ✨ Key Features

### 🚢 Vessel Tracking & Anomaly Detection
- **Real-time AIS (Automatic Identification System) monitoring** - Track vessel movements globally
- **Dark vessel detection** - Identify ships with disabled AIS transponders (common in illegal fishing)
- **Risk scoring algorithm** - ML-based risk assessment for each vessel
- **Behavioral pattern analysis** - Detect suspicious activities and route deviations
- **Multi-vessel tracking** - Simultaneous monitoring of thousands of ships

### 🛢️ Pollution Monitoring
- **Satellite-based pollution detection** - Integrate data from Copernicus/Sentinel satellites
- **Oil spill detection** - Computer vision models for identifying oil slicks
- **Plastic accumulation zones** - Track marine debris hotspots
- **Chemical discharge monitoring** - Detect illegal dumping events
- **Confidence scoring** - AI-powered verification of pollution events (65-92% accuracy)

### 🏝️ Marine Protected Area (MPA) Compliance
- **Boundary monitoring** - Real-time tracking of vessels near MPAs
- **Predictive violation alerts** - LSTM-based route prediction warns of potential MPA entries
- **Compliance reporting** - Automated documentation for enforcement agencies
- **4+ MPAs monitored** - Including Gulf of Mannar, Gulf of Kutch, Gahirmatha Sanctuary, and more

### 🤖 MIA - Marine Intelligence Assistant
- **AI-powered chatbot** - Built with Google Gemini (default model: gemini-2.5-flash)
- **Natural language queries** - Ask questions about vessels, pollution, or MPAs
- **Data synthesis** - Combines AIS data, satellite imagery, and historical patterns
- **Source attribution** - All answers cite data sources with confidence scores
- **Function calling** - Direct database queries for real-time intelligence
- **Conversational memory** - Maintains context across multi-turn conversations

### 📊 Ocean Health Monitoring
- **Ocean Health Index (OHI) tracking** - Monitor ecosystem vitality over time
- **Temperature & pH trends** - Climate change impact visualization
- **Historical data analysis** - 6+ months of time-series data
- **Predictive forecasting** - Prophet-based time-series predictions
- **Interactive charts** - Recharts-powered data visualization

### ⚠️ Intelligent Alert System
- **MPA violation warnings** - Predictive alerts before vessels enter protected zones
- **Pollution event notifications** - Immediate alerts on new detections
- **IUU fishing detection** - Illegal, Unreported, and Unregulated fishing alerts
- **Severity classification** - High/Medium/Low priority levels
- **Real-time feed** - Live alert dashboard with premium UI

---

## 🏭 Industrial Applications

### Government & Maritime Authorities
- **Coast Guard operations** - Real-time vessel monitoring for search & rescue
- **Customs enforcement** - Track suspicious cargo movements
- **Environmental compliance** - Monitor shipping lanes and pollution sources
- **Border security** - Detect unauthorized vessels in territorial waters

### Environmental Organizations
- **MPA enforcement** - Protect marine reserves from illegal fishing
- **Pollution response** - Rapid identification and tracking of spills
- **Wildlife protection** - Monitor vessel traffic near endangered species habitats
- **Climate research** - Long-term ocean health data collection

### Commercial Shipping
- **Fleet management** - Optimize routes and fuel consumption
- **Compliance verification** - Ensure adherence to environmental regulations
- **Risk assessment** - Avoid high-risk areas and bad weather
- **Transparency reporting** - ESG (Environmental, Social, Governance) metrics

### Insurance & Legal
- **Maritime insurance** - Risk-based premium calculations
- **Incident investigation** - Historical vessel tracking and event reconstruction
- **Legal evidence** - Document violations with timestamped data
- **Claims processing** - Verify vessel positions during incidents

---

## 🚀 Future Scope & Roadmap

### Phase 1: Enhanced Detection (Q1-Q2 2026)
- [ ] **Multi-source fusion** - Integrate radar, optical, and SAR satellite data
- [ ] **Advanced ML models** - Upgrade to YOLOv10 for vessel detection
- [ ] **Acoustic monitoring** - Underwater noise pollution tracking
- [ ] **Blockchain ledger** - Immutable incident recording for legal compliance

### Phase 2: Predictive Intelligence (Q3-Q4 2026)
- [ ] **AI route prediction** - 72-hour trajectory forecasting with 90%+ accuracy
- [ ] **Behavioral profiling** - Identify vessel ownership and historical patterns
- [ ] **Climate impact modeling** - Predict ocean health trends 5+ years ahead
- [ ] **Automated reporting** - Generate compliance reports for regulatory bodies

### Phase 3: Global Expansion (2027)
- [ ] **Multi-region support** - Expand from Indian Ocean to Pacific, Atlantic, Arctic
- [ ] **International collaboration** - Integrate with INTERPOL, IMO, FAO fisheries databases
- [ ] **Mobile app** - iOS/Android apps for field enforcement teams
- [ ] **Drone integration** - Connect to UAVs for visual verification of alerts

### Phase 4: Autonomous Operations (2028+)
- [ ] **Autonomous response drones** - Deploy water sampling drones to pollution sites
- [ ] **Edge computing** - Real-time processing on ships and buoys
- [ ] **Quantum computing integration** - Optimize global fleet routing
- [ ] **AI-powered policy recommendations** - Suggest new MPA locations based on data

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│  React + Vite + TailwindCSS + React-Leaflet + Recharts         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Map View    │  │ Alert Feed   │  │ Ocean Health │         │
│  │  (Leaflet)   │  │ (Real-time)  │  │   Charts     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │         MIA Chatbot (Gemini-powered)              │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ REST API (FastAPI)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                 │
│  FastAPI + SQLModel + PostgreSQL/PostGIS + Redis + Celery      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API ENDPOINTS                          │  │
│  │  /map/layers  │ /alerts  │ /analytics  │ /chat/message  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Vessel     │  │  Pollution   │  │     MPA      │         │
│  │   Tracking   │  │  Detection   │  │  Compliance  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AI/ML SERVICES                               │  │
│  │  • Route Predictor (LSTM)                                 │  │
│  │  • Pollution Detector (YOLOv8 + Ultralytics)             │  │
│  │  • Alert Generator (Risk Scoring)                         │  │
│  │  • MIA Chatbot (Google Gemini 2.5 Flash)                 │  │
│  │  • Ocean Health Forecaster (Prophet)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     AIS      │  │  Copernicus  │  │   Protected  │         │
│  │  Ship Data   │  │  Satellites  │  │ Planet APIs  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
blue_guard/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── map.py        # GeoJSON vessel/pollution/MPA layers
│   │   │   ├── alerts.py     # Alert feed endpoint
│   │   │   ├── analytics.py  # Statistics and OHI data
│   │   │   ├── chat.py       # MIA chatbot interface
│   │   │   └── ingest.py     # Data ingestion endpoints
│   │   ├── models/           # SQLModel database models
│   │   │   ├── vessel.py     # VesselTrack, VesselType
│   │   │   ├── pollution.py  # PollutionEvent, PollutionType
│   │   │   ├── mpa.py        # MarineProtectedArea
│   │   │   └── health.py     # OceanHealthMetric
│   │   ├── services/         # Business logic
│   │   │   ├── chatbot.py    # MIA - Gemini integration
│   │   │   ├── alert_generator.py  # Predictive alerts
│   │   │   ├── pollution_detector.py  # YOLOv8 model
│   │   │   ├── route_predictor.py  # LSTM trajectory
│   │   │   └── agent_lightning.py  # RLAF integration
│   │   ├── schemas/          # Pydantic response models
│   │   ├── database.py       # PostgreSQL + PostGIS setup
│   │   ├── config.py         # Environment configuration
│   │   ├── demo_data.py      # Hardcoded demo data
│   │   └── main.py           # FastAPI app initialization
│   ├── scripts/              # Data ingestion scripts
│   │   ├── ingest_ais.py     # AIS data loader
│   │   ├── ingest_sentinel.py  # Satellite imagery
│   │   └── load_mpas.py      # MPA boundary loader
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── map/
│   │   │   │   └── BlueGuardMap.jsx  # Leaflet map
│   │   │   ├── dashboard/
│   │   │   │   ├── AlertFeed.jsx     # Live alerts
│   │   │   │   ├── StatsPanel.jsx    # Key metrics
│   │   │   │   └── HealthCharts.jsx  # OHI graphs
│   │   │   └── chat/
│   │   │       └── ChatBot.jsx       # MIA UI
│   │   ├── App.jsx           # Main app component
│   │   └── main.jsx          # Entry point
│   ├── package.json
│   ├── tailwind.config.js    # Premium blue theme
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml        # Multi-container orchestration
├── .env.example              # Environment template
├── DEMO_SETUP.md             # Hackathon demo guide
└── README.md                 # This file
```

---

## 🛠️ Technology Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool and dev server |
| **TailwindCSS** | Utility-first styling + premium blue theme |
| **React-Leaflet** | Interactive maps with OpenStreetMap |
| **Recharts** | Data visualization (charts/graphs) |
| **Axios** | HTTP client for API calls |
| **Lucide React** | Modern icon library |
| **Radix UI** | Accessible component primitives |
| **React Markdown** | Render MIA responses with formatting |

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance Python web framework |
| **SQLModel** | SQL database ORM (SQLAlchemy + Pydantic) |
| **PostgreSQL + PostGIS** | Geospatial database |
| **Redis** | Caching and message broker |
| **Celery** | Distributed task queue for background jobs |
| **Pydantic** | Data validation and settings management |
| **Uvicorn** | ASGI server |
| **Alembic** | Database migrations |

### AI/ML
| Technology | Purpose |
|------------|---------|
| **Google Gemini** | Conversational AI for MIA chatbot |
| **PyTorch** | Deep learning framework |
| **Ultralytics YOLOv8** | Object detection for pollution |
| **Prophet (Facebook)** | Time-series forecasting |
| **NumPy + Pandas** | Data manipulation |

### Geospatial
| Technology | Purpose |
|------------|---------|
| **GeoAlchemy2** | Spatial query support in SQLAlchemy |
| **Shapely** | Geometric operations |
| **Fiona** | Vector data I/O |
| **PyProj** | Coordinate transformations |

### DevOps
| Technology | Purpose |
|------------|---------|
| **Docker + Docker Compose** | Containerization |
| **Supabase** | Managed PostgreSQL hosting (optional) |
| **GitHub Actions** | CI/CD (future) |

---

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (recommended) OR
- **Python 3.11 or 3.12** (PyTorch 2.2 has no wheels for newer Python) and **Node.js 20.19+**
- **PostgreSQL 15** with **PostGIS 3.3** extension
- **Redis 7**
- **Google Gemini API Key** (for MIA chatbot)

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aditya-Patil27/marine_gurad.git
   cd marine_gurad
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   ```

   Edit `backend/.env` and set:
   ```env
   # Google Gemini API
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

   Docker Compose starts a local PostGIS database and runs the Alembic migrations
   automatically. To use Supabase instead, set `DATABASE_URL` (a `postgresql://`
   connection string) in a root `.env` file or your shell.

3. **Start all services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API Docs: http://localhost:8000/docs
   - Redis: localhost:6379

### Option 2: Manual Setup

#### Backend Setup

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database**
   ```bash
   # Create PostgreSQL database with PostGIS
   createdb blueguard_db
   psql blueguard_db -c "CREATE EXTENSION postgis;"

   # Run migrations
   alembic upgrade head

   # Optional: load sample Marine Protected Areas
   python scripts/load_mpas.py
   ```

4. **Run backend server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```

   Edit `frontend/.env`:
   ```env
   # Empty = use the Vite dev proxy to http://127.0.0.1:8000
   VITE_API_URL=
   VITE_MAP_CENTER_LAT=20.0
   VITE_MAP_CENTER_LNG=77.0
   VITE_MAP_ZOOM=4
   ```

3. **Run development server**
   ```bash
   npm run dev
   ```

4. **Open browser**
   Navigate to http://localhost:5173

---

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Map Layers
```http
GET /api/v1/map/layers?layer_type=vessels&bbox=minLon,minLat,maxLon,maxLat
GET /api/v1/map/layers?layer_type=pollution
GET /api/v1/map/layers?layer_type=mpas
```

#### Analytics
```http
GET /api/v1/analytics/statistics
GET /api/v1/analytics/ohi?timeframe=6months
```

#### Alerts
```http
GET /api/v1/alerts?severity=HIGH&limit=20
```

#### Chat (MIA)
```http
POST /api/v1/chat/message
{
  "message": "Show me high-risk vessels near Mumbai",
  "conversation_history": []
}
```

#### Data Ingestion
```http
POST /api/v1/ingest/ais
POST /api/v1/ingest/pollution
```

---

## 🎨 UI/UX Features

### Premium Blue Theme
- **Ocean-inspired color palette** - 50-950 gradient scale
- **Glassmorphism effects** - Backdrop blur and transparency
- **Gradient backgrounds** - Radial and linear gradients
- **Smooth animations** - Hover effects and transitions
- **Responsive design** - Mobile, tablet, desktop optimized

### Interactive Map
- **Multi-layer visualization** - Vessels, pollution zones, MPAs
- **Clickable markers** - Detailed popup information
- **Dynamic filtering** - Toggle layers on/off
- **Bounding box queries** - Load data for visible area only
- **Risk-based color coding** - Green (low) → Yellow (medium) → Red (high)

### Real-Time Updates
- **Live alert feed** - New alerts appear instantly
- **Auto-refresh statistics** - 30-second polling interval
- **Vessel position updates** - Track ships in real-time
- **Confidence indicators** - Visual cues for data quality

---

## 🧪 Demo Mode

For hackathons and presentations, BlueGuard includes a **demo mode** with hardcoded data:

- **10 vessels** - Around Indian Ocean region
- **5 pollution events** - Oil spills, plastic zones
- **4 MPAs** - Gulf of Mannar, Kutch, etc.
- **7 alerts** - MPA violations, IUU fishing
- **No database required** - All data in-memory

See [DEMO_SETUP.md](DEMO_SETUP.md) for detailed instructions.

---

## 🧠 MIA - Marine Intelligence Assistant

MIA is powered by **Google Gemini** (configurable via `GEMINI_MODEL`) and can answer:

**Example Questions:**
- "Show me all vessels near 20.5°N, 70.2°E"
- "What pollution events were detected this week?"
- "Which MPAs have the most violations?"
- "Is vessel MMSI 123456789 compliant?"
- "Explain the Ocean Health Index trend"

**Function Calling:**
MIA uses Gemini's function calling to execute:
- `query_vessel_intel(mmsi, vessel_type, timeframe)`
- `query_pollution_data(indicator, severity, timeframe)`
- `get_mpa_compliance(mpa_name, metric_type)`

---

## 🔒 Security & Privacy

- **API authentication** - JWT tokens for production (future)
- **CORS policies** - Whitelist allowed origins
- **SQL injection prevention** - Parameterized queries via SQLModel
- **Data anonymization** - No personally identifiable vessel information
- **Rate limiting** - Prevent API abuse (future)

---

## 📈 Performance Metrics

- **Map layer load time**: <2 seconds for 1000+ vessels
- **Alert generation**: Real-time (<1 second)
- **MIA response time**: 2-5 seconds (Gemini Pro)
- **Database query optimization**: PostGIS spatial indexes
- **Frontend bundle size**: ~500KB (gzipped)

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript/React
- Write unit tests for new features
- Update documentation for API changes

## 🙏 Acknowledgments

- **OpenStreetMap** - Map tiles
- **Google Gemini** - AI chatbot capabilities
- **Copernicus/Sentinel** - Satellite imagery APIs
- **MarineCadastre** - AIS vessel data
- **Protected Planet** - MPA boundary data
- **Ocean Health Index** - Ecosystem health metrics

---

## 🔑 API Keys & Configuration

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **Supabase** | PostgreSQL database hosting | [supabase.com](https://supabase.com) |
| **Google Gemini** | MIA chatbot AI | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| **Copernicus Marine** | Satellite ocean data | [Copernicus Data Store](https://data.marine.copernicus.eu/register) |

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database (Supabase PostgreSQL with PostGIS)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Security
SECRET_KEY=your-256-bit-secret-key
JWT_SECRET=your-jwt-secret

# Google Gemini API (required for MIA chatbot)
GEMINI_API_KEY=your-gemini-api-key

# Copernicus Marine Service API
COPERNICUS_CLIENT_ID=your-copernicus-client-id
COPERNICUS_CLIENT_SECRET=your-copernicus-client-secret

# Model Configuration
MODEL_STORAGE_BACKEND=local
YOLO_MODEL_PATH=models/pollution_yolo.pt
LSTM_MODEL_PATH=models/route_lstm.pt
```

---

## 🧠 Model Training

BlueGuard uses two ML models that need to be trained for production use:

### 1. YOLO Pollution Detection Model

The pollution detector uses YOLOv8 to identify oil spills, plastic debris, and algal blooms in satellite imagery.

#### Dataset Preparation

Create a dataset in YOLO format:

```
datasets/pollution/
├── images/
│   ├── train/
│   │   ├── image001.jpg
│   │   └── ...
│   └── val/
├── labels/
│   ├── train/
│   │   ├── image001.txt    # class x_center y_center width height
│   │   └── ...
│   └── val/
└── data.yaml
```

**data.yaml:**
```yaml
path: ./datasets/pollution
train: images/train
val: images/val

names:
  0: OIL
  1: PLASTIC
  2: ALGAE
```

#### Training Script

Create `scripts/train_yolo.py`:

```python
from ultralytics import YOLO
import shutil

# Load pretrained YOLOv8 model
model = YOLO('yolov8n.pt')

# Train on pollution dataset
results = model.train(
    data='datasets/pollution/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='pollution_yolo',
    project='runs/detect'
)

# Copy trained model to models directory
shutil.copy('runs/detect/pollution_yolo/weights/best.pt', 'models/pollution_yolo.pt')
print("Model saved to models/pollution_yolo.pt")
```

Run training:
```bash
cd backend
python scripts/train_yolo.py
```

### 2. LSTM Route Prediction Model

The route predictor uses an LSTM neural network to forecast vessel trajectories.

#### Dataset Preparation

Create `scripts/prepare_lstm_data.py`:

```python
import numpy as np
from app.database import SessionLocal
from app.models.vessel import VesselTrack
from sqlmodel import select
from geoalchemy2.shape import to_shape

def prepare_trajectory_data(sequence_length=10, prediction_steps=6):
    """Extract trajectory sequences from AIS database"""
    db = SessionLocal()

    query = select(VesselTrack).order_by(VesselTrack.mmsi, VesselTrack.timestamp)
    tracks = db.exec(query).all()

    sequences, targets = [], []
    current_mmsi, current_positions = None, []

    for track in tracks:
        if track.mmsi != current_mmsi:
            current_mmsi = track.mmsi
            current_positions = []

        # Extract coordinates from geometry
        point = to_shape(track.location)
        current_positions.append([point.x, point.y])

        # Create sequences when enough positions available
        if len(current_positions) >= sequence_length + prediction_steps:
            seq = current_positions[-sequence_length-prediction_steps:-prediction_steps]
            target = current_positions[-prediction_steps:]
            sequences.append(seq)
            targets.append(target)

    db.close()
    return np.array(sequences), np.array(targets)

if __name__ == "__main__":
    X, y = prepare_trajectory_data()
    np.save('datasets/lstm/X_train.npy', X)
    np.save('datasets/lstm/y_train.npy', y)
    print(f"Saved {len(X)} trajectory sequences")
```

#### Training Script

Create `scripts/train_lstm.py`:

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from app.services.route_predictor import VesselLSTM

# Load data
X = np.load('datasets/lstm/X_train.npy')
y = np.load('datasets/lstm/y_train.npy')

# Normalize
mean, std = X.mean(axis=(0, 1)), X.std(axis=(0, 1)) + 1e-6
X_norm = (X - mean) / std
y_norm = (y - mean) / std

# Create dataloader
dataset = TensorDataset(torch.FloatTensor(X_norm), torch.FloatTensor(y_norm[:, 0, :]))
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# Train
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = VesselLSTM(input_size=2, hidden_size=64, num_layers=2, output_size=2).to(device)
criterion, optimizer = nn.MSELoss(), optim.Adam(model.parameters(), lr=0.001)

for epoch in range(100):
    model.train()
    total_loss = 0
    for batch_X, batch_y in dataloader:
        optimizer.zero_grad()
        loss = criterion(model(batch_X.to(device)), batch_y.to(device))
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    if (epoch + 1) % 10 == 0:
        print(f'Epoch [{epoch+1}/100], Loss: {total_loss/len(dataloader):.6f}')

torch.save(model.state_dict(), 'models/route_lstm.pt')
print("Model saved to models/route_lstm.pt")
```

Run training:
```bash
cd backend
mkdir -p datasets/lstm models
python scripts/prepare_lstm_data.py
python scripts/train_lstm.py
```

### Model Storage Options

BlueGuard supports multiple storage backends for trained models:

| Backend | Configuration | Use Case |
|---------|--------------|----------|
| **Local** | `MODEL_STORAGE_BACKEND=local` | Development, single server |
| **Supabase** | `MODEL_STORAGE_BACKEND=supabase` | Cloud deployment with Supabase |
| **AWS S3** | `MODEL_STORAGE_BACKEND=s3` | Production cloud deployment |
| **HTTP** | `MODEL_STORAGE_BACKEND=http` | CDN-hosted models |

Example S3 configuration:
```env
MODEL_STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_MODEL_BUCKET=blueguard-models
YOLO_MODEL_REMOTE_PATH=pollution_yolo_v1.0.0.pt
LSTM_MODEL_REMOTE_PATH=route_lstm_v1.0.0.pt
```

---

## 📊 Data Ingestion

### AIS Vessel Data

Ingest AIS data from Marine Cadastre CSV files:

```bash
# Using command line argument
python scripts/ingest_ais.py path/to/AIS_data.csv

# Using environment variable
export AIS_CSV_PATH=/path/to/AIS_data.csv
python scripts/ingest_ais.py
```

**Expected CSV columns:**
| Column | Type | Description |
|--------|------|-------------|
| `MMSI` | int | Maritime Mobile Service Identity (required) |
| `LAT`, `LON` | float | Geographic coordinates (required) |
| `BaseDateTime` | datetime | ISO8601 timestamp (required) |
| `SOG`, `COG` | float | Speed/Course over ground |
| `VesselType` | int | AIS vessel type code |
| `VesselName` | string | Ship name |

### Copernicus Satellite Data

The Copernicus Marine Service provides ocean observation data. Use your credentials to access:

- **Sea surface temperature** - Climate monitoring
- **Chlorophyll concentration** - Algal bloom detection
- **Ocean color** - Pollution identification
- **Wave/current data** - Navigation assistance

```python
# Example: Fetching Copernicus data
import requests

auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
response = requests.post(auth_url, data={
    "grant_type": "client_credentials",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
})
access_token = response.json()["access_token"]
```

---

**Built with 💙 for the oceans**

*BlueGuard - Protecting our blue planet through intelligent surveillance*
