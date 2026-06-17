# OLS Marketing Dashboard

A modern React dashboard for managing marketing tasks across multiple channels (SEO, Google Ads, Shopify).

## Features

- Real-time task management with approve/dismiss actions
- Task filtering by status and type
- Visual metrics with KPI cards and charts
- Channel status monitoring (GSC, GA4, Google Ads)
- Dark theme UI with Tailwind CSS
- Auto-refresh every 30 seconds
- Toast notifications for user feedback
- Fully responsive design

## Development

### Setup

```bash
npm install
npm run dev
```

The dev server will start at `http://localhost:5173` and proxy `/api` requests to `http://localhost:8000`.

### Build

```bash
npm run build
```

Output will be in the `dist/` directory.

## Docker

Build and run the dashboard in Docker:

```bash
docker build -t ols-dashboard .
docker run -p 80:80 --network=host ols-dashboard
```

The dashboard will be accessible at `http://localhost` and will proxy API requests to `http://api:8000`.

## Configuration

- **API Key**: Enter in the dashboard unlock screen. It is stored only in this browser's local storage.
- **API URL**: Configure via `VITE_API_URL` environment variable (empty string uses proxy)
- **Theme Colors**: Customize color palette in `src/App.jsx`

## API Endpoints

The dashboard communicates with these backend endpoints:

- `POST /api/dashboard/generate-tasks` - Generate new task recommendations
- `GET /api/dashboard/tasks` - List tasks (supports filtering)
- `POST /api/dashboard/tasks/{id}/approve` - Approve a task
- `POST /api/dashboard/tasks/{id}/dismiss` - Dismiss a task
- `GET /api/dashboard/metrics` - Get dashboard metrics
- `GET /api/dashboard/metrics/channels` - Get channel status metrics

All API requests include the operator-provided `X-API-Key` header for authentication.

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Recharts** - Chart library
- **Lucide React** - Icons
- **Tailwind CSS** - Styling
- **Nginx** - Production web server

## License

Proprietary - Organizing Life Services
