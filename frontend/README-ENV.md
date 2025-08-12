# Frontend Environment Configuration

## Environment Files

This project uses different environment files for different scenarios:

### `.env` (Production)
- **Purpose**: Production configuration
- **Committed**: Yes (tracked by git)
- **API URL**: `https://expense-tracker-backend-7i1w.onrender.com/api/v1`
- **Usage**: Used for production builds and deployments

### `.env.local` (Local Development)
- **Purpose**: Local development configuration
- **Committed**: No (ignored by git)
- **API URL**: `http://localhost:8000/api/v1`
- **Usage**: Used when running `npm run dev` locally

## Quick Start

### For Local Development
```bash
# Make sure .env.local exists with localhost settings
npm run dev
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

### For Production Build
```bash
# Uses .env with production settings
npm run build
```

### To Test Production Settings Locally
```bash
# Temporarily disable local settings
mv .env.local .env.local.backup
npm run dev  # Now uses production .env

# Restore local settings
mv .env.local.backup .env.local
```

## Environment Variables

### Required Variables
- `VITE_API_URL` - Backend API URL
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anonymous key
- `VITE_WS_URL` - WebSocket URL (optional)
- `VITE_NODE_ENV` - Environment mode

### Example `.env.local`
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://nsvdbcqvyphyiktrvtkw.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zdmRiY3F2eXBoeWlrdHJ2dGt3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4ODUzMjUsImV4cCI6MjA2OTQ2MTMyNX0.Mg8xh_x3mXwetx1NU3AocQpV5TovYpl1uxlEHlxFG-s
VITE_WS_URL=ws://localhost:8000/ws
VITE_NODE_ENV=development
```

## Troubleshooting

### "Failed to execute 'json' on 'Response': Unexpected end of JSON input"
This error usually means the frontend is trying to connect to the wrong API URL:

1. Check if `.env.local` exists and has the correct `VITE_API_URL`
2. Make sure your backend is running on `http://localhost:8000`
3. Restart the frontend dev server after changing environment files

### Frontend connects to production instead of local backend
1. Ensure `.env.local` exists with `VITE_API_URL=http://localhost:8000/api/v1`
2. Check browser console for "API Configuration" logs
3. Restart `npm run dev` after creating/modifying `.env.local`