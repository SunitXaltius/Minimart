# CI/CD Notes

## Prompt-to-commit workflow

Keep the prompt-log update in the same commit as the AI-assisted code change it produced.

## Gate that would have caught a real bug

The role-based access test would have caught the earlier flaw that allowed a shopper to reach `/admin`. Removing `admin_required` makes that test fail before merge.
