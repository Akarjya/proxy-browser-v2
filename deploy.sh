#!/bin/bash

# Deploy script for Proxy Browser V2

echo "🚀 Starting deployment process..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required commands
if ! command_exists git; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Deploy to Railway
deploy_railway() {
    echo "🚂 Deploying to Railway..."
    
    if ! command_exists railway; then
        echo "Installing Railway CLI..."
        npm install -g @railway/cli
    fi
    
    railway login
    railway up
    echo "✅ Railway deployment complete!"
}

# Deploy to Render
deploy_render() {
    echo "🎨 Deploying to Render..."
    echo "1. Go to https://render.com/"
    echo "2. Connect your GitHub repository"
    echo "3. Select 'New Web Service'"
    echo "4. Choose your repository"
    echo "5. Render will use render.yaml automatically"
    echo "✅ Follow the steps above to complete Render deployment"
}

# Deploy to Heroku
deploy_heroku() {
    echo "🟣 Deploying to Heroku..."
    
    if ! command_exists heroku; then
        echo "❌ Heroku CLI not installed. Install from: https://devcenter.heroku.com/articles/heroku-cli"
        exit 1
    fi
    
    # Create Procfile
    echo "web: uvicorn app.core.app:app --host 0.0.0.0 --port \$PORT" > Procfile
    
    heroku create proxy-browser-v2
    git add .
    git commit -m "Add Heroku deployment files"
    git push heroku main
    echo "✅ Heroku deployment complete!"
}

# Main menu
echo "Choose deployment platform:"
echo "1) Railway (Recommended - Easy & Fast)"
echo "2) Render (Good free tier)"
echo "3) Heroku (Traditional choice)"
echo "4) Exit"

read -p "Enter your choice [1-4]: " choice

case $choice in
    1)
        deploy_railway
        ;;
    2)
        deploy_render
        ;;
    3)
        deploy_heroku
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting..."
        exit 1
        ;;
esac

echo "🎉 Deployment process finished!"
