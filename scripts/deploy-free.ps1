# Free Deployment Script for Windows
Write-Host "🆓 Free Deployment - Expense Tracker" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Check if git repo is clean
Write-Host "📋 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️  Please commit your changes first:" -ForegroundColor Yellow
    Write-Host $gitStatus -ForegroundColor Red
    Write-Host ""
    Write-Host "Run these commands first:" -ForegroundColor Yellow
    Write-Host "  git add ." -ForegroundColor White
    Write-Host "  git commit -m 'Prepare for deployment'" -ForegroundColor White
    exit 1
}

# Check if we're on main branch
$currentBranch = git branch --show-current
if ($currentBranch -ne "main") {
    Write-Host "⚠️  Please switch to main branch first:" -ForegroundColor Yellow
    Write-Host "  git checkout main" -ForegroundColor White
    exit 1
}

# Push to trigger deployments
Write-Host "📤 Pushing to GitHub to trigger deployments..." -ForegroundColor Yellow
try {
    git push origin main
    Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to push to GitHub" -ForegroundColor Red
    Write-Host "Make sure you have a GitHub repository set up:" -ForegroundColor Yellow
    Write-Host "  git remote add origin https://github.com/yourusername/expense-tracker.git" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "🚀 Deployment triggered!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Free Tier Services:" -ForegroundColor Cyan
Write-Host "   🌐 Frontend: Netlify (100GB bandwidth/month)" -ForegroundColor White
Write-Host "   ⚡ Backend:  Render (750 hours/month)" -ForegroundColor White
Write-Host "   🗄️  Database: Supabase (500MB storage)" -ForegroundColor White
Write-Host ""
Write-Host "🔗 Check deployment status:" -ForegroundColor Cyan
Write-Host "   Render Dashboard:  https://dashboard.render.com" -ForegroundColor White
Write-Host "   Netlify Dashboard: https://app.netlify.com" -ForegroundColor White
Write-Host "   Supabase Dashboard: https://supabase.com/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "⏱️  Deployment Progress:" -ForegroundColor Yellow
Write-Host "   • Backend build: ~3-5 minutes" -ForegroundColor White
Write-Host "   • Frontend build: ~1-2 minutes" -ForegroundColor White
Write-Host "   • Total time: ~5-7 minutes" -ForegroundColor White
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Wait for deployments to complete" -ForegroundColor White
Write-Host "   2. Get your backend URL from Render" -ForegroundColor White
Write-Host "   3. Update VITE_API_URL in Netlify environment variables" -ForegroundColor White
Write-Host "   4. Update CORS origins in your backend code" -ForegroundColor White
Write-Host "   5. Test your live application!" -ForegroundColor White
Write-Host ""
Write-Host "💡 Pro Tips:" -ForegroundColor Cyan
Write-Host "   • Render free tier sleeps after 15 min - use UptimeRobot to keep awake" -ForegroundColor White
Write-Host "   • First request after sleep takes ~30 seconds (normal)" -ForegroundColor White
Write-Host "   • All services provide free SSL certificates" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Your app will be live at:" -ForegroundColor Green
Write-Host "   Frontend: https://your-app-name.netlify.app" -ForegroundColor White
Write-Host "   Backend:  https://your-backend-name.onrender.com" -ForegroundColor White