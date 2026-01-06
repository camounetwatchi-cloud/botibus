---
description: Deploy changes to GitHub and verify Actions
---
# Deployment Workflow

1. Check status of files to be committed.
// turbo
2. git status

3. Stage all changes (or selectively stage if you prefer).
// turbo
4. git add .

5. Commit with a meaningful message.
   - Example: `git commit -m "feat: optimize agent workflow"`

6. Push to the main branch.
// turbo
7. git push origin main

8. Verify the GitHub Action run status.
// turbo
9. gh run list --workflow=trading_bot.yml --limit 3
