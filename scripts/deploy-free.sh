#!/bin/bash

# Free Deployment Script for Linux/Mac
echo "🆓 Free Deployment - Expense Tracker"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Check if git repo is clean
echo -e "${YELLOW}📋 Checking git status...${NC}"
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  Please commit your changes first:${NC}"
    git status --porcelain
    echo ""
    echo -e "${YELLOW}Run these commands first:${NC}"
    echo -e "${WHITE}  git add .${NC}"
    echo -e "${WHITE}  git commit -m 'Prepare for deployment'${NC}"
    exit 1
fi

# Check if we're on main branch
current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" ]]; then
    echo -e "${YELLOW}⚠️  Please switch to main branch first:${NC}"
    echo -e "${WHITE}  git checkout main${NC}"
    exit 1
fi

# Push to trigger deployments
echo -e "${YELLOW}📤 Pushing to GitHub to trigger deployments...${NC}"
if git push origin main; then
    echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
else
    echo -e "${RED}❌ Failed to push to GitHub${NC}"
    echo -e "${YELLOW}Make sure you have a GitHub repository set up:${NC}"
    echo -e "${WHITE}  git remote add origin https://github.com/yourusername/expense-tracker.git${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 Deployment triggered!${NC}"
echo ""
echo -e "${CYAN}📊 Free Tier Services:${NC}"
echo -e "${WHITE}   🌐 Frontend: Netlify (100GB bandwidth/month)${NC}"
echo -e "${WHITE}   ⚡ Backend:  Render (750 hours/month)${NC}"
echo -e "${WHITE}   🗄️  Database: Supabase (500MB storage)${NC}"
echo ""
echo -e "${CYAN}🔗 Check deployment status:${NC}"
echo -e "${WHITE}   Render Dashboard:  https://dashboard.render.com${NC}"
echo -e "${WHITE}   Netlify Dashboard: https://app.netlify.com${NC}"
echo -e "${WHITE}   Supabase Dashboard: https://supabase.com/dashboard${NC}"
echo ""
echo -e "${YELLOW}⏱️  Deployment Progress:${NC}"
echo -e "${WHITE}   • Backend build: ~3-5 minutes${NC}"
echo -e "${WHITE}   • Frontend build: ~1-2 minutes${NC}"
echo -e "${WHITE}   • Total time: ~5-7 minutes${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo -e "${WHITE}   1. Wait for deployments to complete${NC}"
echo -e "${WHITE}   2. Get your backend URL from Render${NC}"
echo -e "${WHITE}   3. Update VITE_API_URL in Netlify environment variables${NC}"
echo -e "${WHITE}   4. Update CORS origins in your backend code${NC}"
echo -e "${WHITE}   5. Test your live application!${NC}"
echo ""
echo -e "${CYAN}💡 Pro Tips:${NC}"
echo -e "${WHITE}   • Render free tier sleeps after 15 min - use UptimeRobot to keep awake${NC}"
echo -e "${WHITE}   • First request after sleep takes ~30 seconds (normal)${NC}"
echo -e "${WHITE}   • All services provide free SSL certificates${NC}"
echo ""
echo -e "${GREEN}🎉 Your app will be live at:${NC}"
echo -e "${WHITE}   Frontend: https://your-app-name.netlify.app${NC}"
echo -e "${WHITE}   Backend:  https://your-backend-name.onrender.com${NC}"