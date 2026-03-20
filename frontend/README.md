# Trading Cards Frontend

React frontend for the Trading Card Platform.

## Tech Stack
- React 18 + Vite
- Tailwind CSS
- Recharts (charts)
- React Router DOM
- Axios (API client)

## Setup

```bash
cd frontend
npm install
npm run dev
```

Dev server: http://localhost:3000

## Build

```bash
npm run build    # Output in dist/
npm run preview  # Preview production build
```

## API Connection

Connects to backend at `http://localhost:8000`. Start the API first:
```bash
/usr/bin/python3 -m backend.api.run
```

## Pages

- `/` - Opportunities (arbitrage finder with card images, buy links)
- `/card/:id` - Card detail with price history
- `/inventory` - Portfolio tracking with P&L
- `/watchlist` - Price monitoring with alerts
