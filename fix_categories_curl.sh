#!/bin/bash

# Get admin token
ADMIN_TOKEN=$(curl -s -X POST "https://api.projectdevops.in/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=admin&password=Gyanu@9693894505" | jq -r '.access_token')

echo "Admin Token: ${ADMIN_TOKEN:0:30}..."
echo ""

# The article that has categories as array ['Patna', 'Buxar'] needs to be updated
# We need to find the article ID first, but since the GET is failing, 
# we'll need to provide the article ID manually

echo "To update an article's categories from array to string, use:"
echo ""
echo "curl -X PUT 'https://api.projectdevops.in/news/ARTICLE_ID' \\"
echo "  -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "  -F 'categories=Patna'"
echo ""
echo "Replace ARTICLE_ID with the actual ID of the article you want to update"
echo ""
echo "Example with a test ID:"
echo ""
echo "curl -X PUT 'https://api.projectdevops.in/news/675643dbb234c8e62e580b4c' \\"
echo "  -H 'Authorization: Bearer $ADMIN_TOKEN' \\"
echo "  -F 'categories=Patna'"

