# Free Deployment Guide

Deploy your Expense Tracker application **completely free** using these platforms with generous free tiers.

## 🆓 100% Free Option: Netlify + Render + Supabase

**Total Cost**: $0/month forever (within free tier limits)

### Architecture
```mermaid
graph TB
    subgraph "Free Tier Services"
        FE[Netlify<br/>Frontend<br/>FREE]
        BE[Render<br/>Backend<br/>FREE]
        DB[Supabase<br/>Database<br/>FREE]
    end
    
    U[Users] --> FE
    FE --> BE
    BE --> DB
```

### Free Tier Limits
- **Netlify**: 100GB bandwidth/month, unlimited sites
- **Render**: 750 hours/month (enough for 24/7), 512MB RAM
- **Supabase**: 500MB database, 2GB bandwidth, 50K users

---

## Step-by-Step Free Deployment

### 1. Prepare Your Code

First, let's prepare your application for free deployment:

```bash
# 1. Create production environment for backend
cd backend
echo "DEBUG=false" > .env.production

# 2. Update CORS for your future domains
# We'll update this after deployment
```

### 2. Deploy Backend to Render (FREE)

1. **Go to [render.com](https://render.com)** and sign up with GitHub
2. **Connect your repository**
3. **Create a Web Service** with these settings:
   - **Name**: `expense-tracker-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`

4. **Add Environment Variables** in Render dashboard:
   ```
   SUPABASE_URL=https://nsvdbcqvyphyiktrvtkw.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zdmRiY3F2eXBoeWlrdHJ2dGt3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4ODUzMjUsImV4cCI6MjA2OTQ2MTMyNX0.Mg8xh_x3mXwetx1NU3AocQpV5TovYpl1uxlEHlxFG-s
   SECRET_KEY=your-secure-production-secret-key-change-this
   DEBUG=false
   ```

5. **Deploy** - Render will automatically build and deploy

Your backend will be available at: `https://expense-tracker-backend-xxxx.onrender.com`

### 3. Deploy Frontend to Netlify (FREE)

1. **Go to [netlify.com](https://netlify.com)** and sign up with GitHub
2. **Connect your repository**
3. **Configure build settings**:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`

4. **Add Environment Variables** in Netlify dashboard:
   ```
   VITE_API_URL=https://your-backend-url.onrender.com/api/v1
   ```
   (Replace with your actual Render backend URL)

5. **Deploy** - Netlify will automatically build and deploy

Your frontend will be available at: `https://your-app-name.netlify.app`

### 4. Update Backend CORS

After both are deployed, update your backend CORS settings:

```python
# In backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app-name.netlify.app",  # Your actual Netlify URL
        "http://localhost:3000",              # Keep for development
        "http://localhost:5173"               # Keep for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push - Render will automatically redeploy.

---

## Alternative Free Options

### Option 2: Vercel + Render + Supabase

**Frontend**: Vercel (100GB bandwidth/month)
**Backend**: Render (750 hours/month)
**Database**: Supabase (500MB storage)

Same process as above, but deploy frontend to Vercel instead of Netlify.

### Option 3: GitHub Pages + Railway + Supabase

**Frontend**: GitHub Pages (1GB storage, unlimited bandwidth)
**Backend**: Railway (500 hours/month on free trial)
**Database**: Supabase (500MB storage)

### Option 4: Surge.sh + Render + Supabase

**Frontend**: Surge.sh (unlimited sites, custom domains)
**Backend**: Render (750 hours/month)
**Database**: Supabase (500MB storage)

---

## Free Deployment Scripts

Create these scripts to automate free deployment:

**deploy-free.ps1** (Windows):
```powershell
# Free Deployment Script
Write-Host "🆓 Deploying to free tier services..." -ForegroundColor Green

# Check if git repo is clean
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️  Please commit your changes first" -ForegroundColor Yellow
    exit 1
}

# Push to trigger deployments
Write-Host "📤 Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host "✅ Deployment triggered!" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Check deployment status:" -ForegroundColor Cyan
Write-Host "   Render:  https://dashboard.render.com" -ForegroundColor White
Write-Host "   Netlify: https://app.netlify.com" -ForegroundColor White
Write-Host ""
Write-Host "⏱️  Deployment usually takes 2-5 minutes" -ForegroundColor Yellow
```

**deploy-free.sh** (Linux/Mac):
```bash
#!/bin/bash
echo "🆓 Deploying to free tier services..."

# Check if git repo is clean
if [[ -n $(git status --porcelain) ]]; then
    echo "⚠️  Please commit your changes first"
    exit 1
fi

# Push to trigger deployments
echo "📤 Pushing to GitHub..."
git push origin main

echo "✅ Deployment triggered!"
echo ""
echo "🔗 Check deployment status:"
echo "   Render:  https://dashboard.render.com"
echo "   Netlify: https://app.netlify.com"
echo ""
echo "⏱️  Deployment usually takes 2-5 minutes"
```

---

## Free Tier Monitoring

### Render Free Tier
- **750 hours/month** (31 days × 24 hours = 744 hours)
- **Sleeps after 15 minutes** of inactivity
- **Cold start time**: ~30 seconds

### Netlify Free Tier
- **100GB bandwidth/month**
- **300 build minutes/month**
- **Always on** (no sleeping)

### Supabase Free Tier
- **500MB database storage**
- **2GB bandwidth/month**
- **50,000 monthly active users**
- **Always on**

---

## Keeping Your App Awake (Free)

Since Render free tier sleeps after 15 minutes, you can use these free services to keep it awake:

### Option 1: UptimeRobot (Free)
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add your Render backend URL
3. Set check interval to 5 minutes
4. Free tier: 50 monitors, 5-minute intervals

### Option 2: Cron-job.org (Free)
1. Sign up at [cron-job.org](https://cron-job.org)
2. Create a job to ping your backend every 10 minutes
3. URL: `https://your-backend.onrender.com/health`

---

## Free Custom Domains

### Netlify
- **Free custom domain**: Connect your own domain for free
- **Free SSL**: Automatic HTTPS certificates

### Render
- **Free custom domain**: Connect your own domain for free
- **Free SSL**: Automatic HTTPS certificates

### Example with Custom Domain
1. Buy domain from Namecheap (~$10/year)
2. Point `api.yourdomain.com` to Render
3. Point `yourdomain.com` to Netlify
4. Both services provide free SSL

---

## Free Tier Limitations & Solutions

### Render Limitations
- **Sleeps after 15 minutes**: Use UptimeRobot to keep awake
- **512MB RAM**: Sufficient for FastAPI + small database operations
- **Slow cold starts**: First request after sleep takes ~30 seconds

### Netlify Limitations
- **100GB bandwidth**: More than enough for most personal projects
- **300 build minutes**: ~10 builds per day

### Supabase Limitations
- **500MB storage**: Good for thousands of expenses
- **2GB bandwidth**: Sufficient for personal use

---

## Cost Comparison

| Service | Free Tier | Paid Tier | When to Upgrade |
|---------|-----------|-----------|-----------------|
| **Render** | 750 hours/month | $7/month | Need 24/7 uptime |
| **Netlify** | 100GB bandwidth | $19/month | High traffic |
| **Supabase** | 500MB storage | $25/month | Need more storage |

**Total Free**: $0/month
**Total Paid**: $51/month (if you need all paid tiers)

---

## Success Checklist

After deployment, verify everything works:

- [ ] ✅ Backend health check: `https://your-backend.onrender.com/health`
- [ ] ✅ Frontend loads: `https://your-app.netlify.app`
- [ ] ✅ Registration works
- [ ] ✅ Login works
- [ ] ✅ Create expense works
- [ ] ✅ CORS is properly configured
- [ ] ✅ Environment variables are set

---

## Troubleshooting Free Deployments

### Common Issues

1. **Build Fails on Render**
   - Check `requirements.txt` is in backend folder
   - Verify Python version compatibility

2. **Frontend Can't Reach Backend**
   - Check `VITE_API_URL` environment variable
   - Verify CORS origins in backend

3. **Render App Sleeps**
   - Set up UptimeRobot monitoring
   - First request after sleep is slow (normal)

4. **Netlify Build Fails**
   - Check build command and publish directory
   - Verify Node.js version compatibility

### Debug Commands

```bash
# Check Render logs
curl https://your-backend.onrender.com/health

# Check Netlify deployment
curl https://your-app.netlify.app

# Test API connection
curl https://your-backend.onrender.com/api/v1/categories
```

---

## 🎉 You're Live!

Your expense tracker is now running **completely free** on professional-grade infrastructure:

- ✅ **Global CDN** (Netlify)
- ✅ **Auto-scaling backend** (Render)
- ✅ **Production database** (Supabase)
- ✅ **Free SSL certificates**
- ✅ **Automatic deployments**

**Total monthly cost: $0** 🎉