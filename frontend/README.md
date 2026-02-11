# Trading Cards Frontend

React frontend for the Trading Card Platform.

## Features

- 🔥 Trending cards table with hotness scores
- 📊 Price history charts
- 💰 Profit calculator
- 🎯 Buy recommendations
- 📈 Card detail pages

## Setup

### Prerequisites

Node.js 16+ required. Update Node if needed:

```bash
# Check version
node --version

# If < 16, update Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Install Dependencies

```bash
cd frontend
npm install
```

### Start Development Server

```bash
npm run dev
```

Visit: http://localhost:3000

## Build for Production

```bash
npm run build
```

Output in `dist/` folder.

## API Connection

Frontend connects to backend API at `http://localhost:8000`

Make sure the API is running:
```bash
python3 -m backend.api.run
```

## Pages

- **Home** (`/`) - Trending cards table
- **Card Detail** (`/card/:id`) - Detailed card view with charts

## Components

- `TrendingTable` - Displays trending cards
- `PriceChart` - Line chart of price history
- `ProfitCalculator` - Calculate buy/sell profit

## Tech Stack

- React 18
- Vite
- TailwindCSS
- Recharts
- React Router
- Axios
