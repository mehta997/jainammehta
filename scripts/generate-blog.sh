#!/bin/bash

TOPIC="$1"
DATE=$(date +"%Y-%m-%d")
SLUG=$(echo "$TOPIC" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 ]//g' | tr ' ' '-')

BLOG_PATH="blog/$SLUG.html"
TEMPLATE="scripts/blog-template.html"
PROMPT="scripts/prompt.txt"

echo "Generating blog: $TOPIC"

CONTENT=$(ollama run llama3 <<EOF
$(sed "s/{{TOPIC}}/$TOPIC/g" $PROMPT)
EOF
)

HTML=$(sed \
  -e "s|{{TITLE}}|$TOPIC|g" \
  -e "s|{{DESCRIPTION}}|$TOPIC - by Jainam Mehta|g" \
  -e "s|{{DATE}}|$DATE|g" \
  -e "s|{{SLUG}}|$SLUG|g" \
  -e "s|{{CONTENT}}|$CONTENT|g" \
  $TEMPLATE)

echo "$HTML" > "$BLOG_PATH"

echo "Blog created at $BLOG_PATH"
