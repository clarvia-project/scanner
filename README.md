# Clarvia AEO Scanner

Scan any URL to measure AI Engine Optimization (AEO) readiness. Get a Clarvia Score across 4 dimensions: API Accessibility, Data Structuring, Agent Compatibility, and Trust Signals.

## Architecture

```
scanner/
  backend/          FastAPI (Python 3.12+)
    app/
      checks/       Scoring modules (13 sub-factors)
      routes/       Stripe payment endpoints
      services/     Supabase + PDF generation
    schema.sql      Database schema
    Dockerfile
  frontend/         Next.js 16 + Tailwind 4
    app/
      page.tsx      Landing page
      scan/[id]/    Scan results
      report/[id]/  Paid report page
    Dockerfile
    vercel.json
  docker-compose.yml
```

## Quick Start (Development)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your keys (optional — works without Stripe/Supabase)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000

### Docker Compose

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

## Environment Variables

See `backend/.env.example` and `frontend/.env.example` for all configuration options.

**Required for core scanning**: None (works out of the box)

**Optional integrations**:
- `SCANNER_STRIPE_SECRET_KEY` — Enable $29 paid reports
- `SCANNER_SUPABASE_URL` + `SCANNER_SUPABASE_ANON_KEY` — Persistent scan storage
- Run `schema.sql` in Supabase SQL Editor to create tables

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scan` | Run a scan (`{"url": "stripe.com"}`) |
| `GET` | `/api/scan/{scan_id}` | Get cached scan result |
| `POST` | `/api/waitlist` | Join waitlist (`{"email": "..."}`) |
| `POST` | `/api/report/create-checkout` | Create Stripe checkout |
| `POST` | `/api/report/webhook` | Stripe webhook handler |
| `GET` | `/api/report/{scan_id}` | Get full paid report |
| `GET` | `/api/report/{scan_id}/pdf` | Download PDF report |
| `GET` | `/health` | Health check |

## Scoring Dimensions (100 points)

- **API Accessibility (25)**: Endpoint existence, response speed, auth documentation
- **Data Structuring (25)**: Schema definition (+ GraphQL bonus), pricing quantified, error structure
- **Agent Compatibility (25)**: MCP server (mcp.so, smithery.ai, glama.ai), robots.txt, sitemap/discovery
- **Trust Signals (25)**: Uptime (+ GitHub stars bonus), documentation quality, update frequency
- **Onchain Bonus (+25)**: Transaction success rate, real volume, staking (V2)

## Rate Limits

- Free: 10 scans/hour per IP
- API key: 100 scans/hour (pass `X-API-Key` header)

## Deployment

- **Frontend**: Deploy to Vercel (`vercel.json` included)
- **Backend**: Deploy via Docker (`Dockerfile` included)
- **Database**: Create a Supabase project and run `schema.sql`
