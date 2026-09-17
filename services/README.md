# services

Background services that sit next to the API. Planned:

- `orchestrator/`: Node.js + BullMQ job queue on Redis
- `edge-filter/`: C++17 geofence filter that drops routine AIS pings before they reach the API
