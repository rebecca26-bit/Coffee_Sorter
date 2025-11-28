#!/bin/bash

# Script to commit and push Coffee Sorter files to GitHub

echo "Coffee Sorter GitHub Push Script"
echo "================================"

# Check if Git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
else
    echo "Git repository already initialized."
fi

# Add all files
echo "Adding files..."
git add .

# Commit with a message
echo "Committing files..."
git commit -m "Add Coffee Sorter project with ML, ThingSpeak, and sensor integration"

# Prompt for GitHub repo URL
echo "https://github.com/rebecca26-bit/Coffee_Sorter.git"
read repo_url

# Add remote origin
echo "Adding remote origin..."
git remote add origin "$repo_url"

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

echo "Done! Check your GitHub repository."
