# PoliceOSINT — AI-Powered Cyber Crime Investigation Platform

Built during internship at **Gurugram Police Cyber Cell (GPCSSI)**

## Features
- 10 OSINT investigation modules
- Internet scam intelligence hub
- 3D cryptocurrency wallet atom graph
- IPDR PDF analyzer
- AI Copilot (Groq/Llama-3.3-70b)
- PDF report generation (FIR Support, Intelligence, Suspect Profile)
- Telegram member profiling
- JWT auth with 8-role RBAC
- 55 unit tests passing

## Stack
Next.js 14 · FastAPI · PostgreSQL · Redis · Docker · Three.js

## Setup
```bash
cp .env.example .env  # Add your API keys
docker compose up -d
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/api/docs
```

## Demo credentials
| Role | Badge | Password |
|---|---|---|
| Inspector | GGN/CYB/2024/001 | Inspector@1234 |
| Analyst | GGN/CYB/2024/002 | Analyst@1234 |
