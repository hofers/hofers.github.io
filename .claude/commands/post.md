---
description: Create a new blog post
---

Create a new blog post with the specified title. Usage: `/post "My Post Title"`

```bash
TITLE="$ARGUMENTS"
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
FILE="_posts/class/$DATE-$SLUG.md"

cat > "$FILE" << EOF
---
layout: default
title: "$TITLE"
date: $DATE
tags: class
---

# $TITLE

Your content here...
EOF

echo "Created new post: $FILE"
```