---
description: Create a new portfolio item
---

Create a new portfolio item with the specified title. Usage: `/portfolio "Project Name"`

```bash
TITLE="$ARGUMENTS"
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
FILE="_portfolio-items/$SLUG.md"

cat > "$FILE" << EOF
---
layout: default
title: "$TITLE"
permalink: /portfolio/$SLUG/
tags: portfolio
image: # Add image filename
link: # Add external link if applicable
description: # Add brief description
---

# $TITLE

Project description and details...
EOF

echo "Created new portfolio item: $FILE"
```