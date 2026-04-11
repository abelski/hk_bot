---
name: User reviews before pushing
description: User wants to review changes before git push — only prepare/stage, never push autonomously
type: feedback
---

Always prepare and commit changes locally but never `git push` unless the user explicitly asks.

**Why:** User prefers to review diffs before pushing to remote.

**How to apply:** Stage and commit freely, but stop before push and tell the user the changes are ready to review and push.
