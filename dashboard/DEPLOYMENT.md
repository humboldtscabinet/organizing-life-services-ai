# OLS Marketing Dashboard - Deployment Guide

## Quick Start

### Development

```bash
cd dashboard
npm install
npm run dev
```

Visit `http://localhost:5173`

### Production (Docker)

```bash
cd dashboard
docker build -t ols-dashboard .
docker run -p 80:80 --network=host ols-dashboard
```

Visit `http://localhost`

## Architecture

### File Structure

```
dashboard/
├── src/
│   ├── App.jsx              # Main dashboard component (all-in-one)
│   ├── api.js              # API client with all endpoints
│   └── main.jsx            # React entry point
├── index.html              # Vite HTML template
├── vite.config.js          # Vite configuration with proxy
├── package.json            # Dependencies
├── Dockerfile              # Multi-stage Docker build
├── nginx.conf              # Production web server config
├── README.md               # User documentation
└── DEPLOYMENT.md           # This file
```

### Key Features Implemented

1. **Dashboard Header**
   - "Generate Tasks" button with loading state
   - Refresh button with spinner
   - Auto-refresh every 30 seconds

2. **KPI Cards** (Top Row)
   - Pending Tasks (yellow badge)
   - Completed Today (green badge)
   - High Priority Tasks (red badge)
   - Active Channels (blue badge)

3. **Charts** (Middle Row)
   - Tasks by Type (Donut/Pie chart)
   - Tasks by Priority (Bar chart)

4. **Task Queue** (Main Section)
   - Status filters: All, Pending, Approved, Completed, Dismissed
   - Type filter dropdown: All Types, SEO, Ads, Shopify
   - Task cards with:
     - Priority badge (color-coded)
     - Type badge (color-coded)
     - Title and description
     - Finding text
     - Timestamps
     - Approve/Dismiss buttons (pending tasks only)
     - Status badge (non-pending tasks)

5. **Channel Status** (Bottom Row)
   - GSC, GA4, Google Ads status cards
   - Record counts and last sync dates

6. **User Experience**
   - Toast notifications on success/error
   - Loading states for all async operations
   - Error handling with user feedback
   - Dark theme consistent with n8n design
   - Fully responsive layout
   - Color-coded priorities and task types

## API Integration

All requests include the `X-API-Key` header supplied by the operator in the
dashboard unlock screen. The key is stored in this browser's local storage and
is not committed to the source bundle.

### Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/dashboard/generate-tasks | Generate task recommendations |
| GET | /api/dashboard/tasks | List all tasks (with filters) |
| POST | /api/dashboard/tasks/{id}/approve | Approve a task |
| POST | /api/dashboard/tasks/{id}/dismiss | Dismiss a task |
| GET | /api/dashboard/metrics | Get dashboard metrics |
| GET | /api/dashboard/metrics/channels | Get channel status |

## Docker Deployment

### Build Process

1. **Stage 1 (Node 20 Alpine)**
   - Install dependencies with `npm ci`
   - Build production bundle with `npm run build`
   - Output: `/app/dist` directory

2. **Stage 2 (Nginx Alpine)**
   - Copy built files to `/usr/share/nginx/html`
   - Copy custom nginx config
   - Expose port 80
   - Start nginx in foreground mode

### Nginx Configuration

- Serves static files from `/usr/share/nginx/html`
- Proxies `/api/*` requests to `http://api:8000`
- SPA fallback: serves `index.html` for all non-file routes
- Gzip compression enabled
- Cache headers for optimal performance
- Health check endpoint at `/health`

## Environment Configuration

### Development (Vite Proxy)

The Vite dev server automatically proxies `/api` requests to `http://localhost:8000`.

No environment variables needed - just start with `npm run dev`.

### Production (Nginx Proxy)

The nginx config proxies `/api` requests to `http://api:8000` (Docker internal network).

If you need a different API URL, modify the nginx config:
```nginx
proxy_pass http://your-api-host:8000;
```

## Theme & Styling

Dark theme colors:
- Background: `#1a1a2e` (dark gray)
- Card Background: `#16213e` (darker blue)
- Accent: `#0f3460` (accent blue)
- Text: `#e0e0e0` (light gray)
- Text Dim: `#a0a0a0` (medium gray)

Task Type Colors:
- SEO: `#3b82f6` (blue)
- Ads: `#a855f7` (purple)
- Shopify: `#10b981` (green)

Priority Colors:
- HIGH: `#ef4444` (red)
- MEDIUM: `#eab308` (yellow)
- LOW: `#10b981` (green)

## Troubleshooting

### API Connection Issues

**In Development:**
- Ensure API is running on `http://localhost:8000`
- Check that `vite.config.js` proxy is configured correctly
- Re-enter the API key in the dashboard unlock screen

**In Docker:**
- Ensure API service is on the same Docker network
- Check nginx config points to correct API host
- Verify Docker network is created: `docker network create ols-network`
- Run with: `docker run --network=ols-network ols-dashboard`

### Build Issues

```bash
# Clear node_modules and rebuild
rm -rf node_modules dist package-lock.json
npm install
npm run build
```

### Chart Rendering Issues

Charts use Recharts and require data to render. Check:
- Metrics API endpoint returns valid data
- Browser console for JavaScript errors
- Recharts library is properly installed

## Performance Optimization

- Auto-refresh: 30 seconds (configurable in `App.jsx`)
- Gzip compression enabled in nginx
- Static asset caching with 1-year expiration
- SPA optimization with proper cache headers
- Docker layer caching for faster rebuilds

## Security

- API key is operator-entered and stored only in browser local storage
- CORS headers managed by nginx proxy
- Do not expose the dashboard outside localhost/Tailscale without stronger auth
- All API requests use HTTPS (when deployed)

## Future Enhancements

- Export tasks to CSV/PDF
- Task scheduling and automation
- User preferences and settings
- Real-time updates with WebSockets
- Task history and audit logs
- Team collaboration features
