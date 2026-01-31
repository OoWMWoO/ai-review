# AI PR Review

Automated GitHub PR code reviews powered by Claude Code.

## Features

- Automatic PR reviews on PR open/update
- On-demand reviews via PR comment ("hey ai review")
- Analyzes code quality and security
- Posts review comments directly to the PR

## TL;DR - Run the Services

```bash
# Terminal 1: Start smee proxy (replace YOUR_CHANNEL with your smee.io URL)
smee -u https://smee.io/YOUR_CHANNEL -t http://localhost:3000

# Terminal 2: Start webhook listener
uv run python webhook_listener.py
```

Both must be running for automated PR reviews to work.

## Prerequisites

- [Claude Code CLI](https://claude.ai/claude-code) installed and logged in
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- [direnv](https://direnv.net/) (optional, for auto-loading env vars)
- [Docker](https://www.docker.com/) (for GitHub MCP server)
- Python 3.13+ with [uv](https://github.com/astral-sh/uv)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/OoWMWoO/ai-review.git
cd ai-review

# Install dependencies
uv sync
```

### 2. Configure Environment

Create a `.env` file:

```bash
# GitHub Personal Access Token (for MCP server)
# Create at: https://github.com/settings/tokens
# Required scopes: repo (for private repos) or public_repo
GITHUB_TOKEN=ghp_your_token_here

# Webhook secret (generate with: openssl rand -hex 32)
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
```

If using direnv:
```bash
direnv allow
```

### 3. Manual Review (Interactive)

Review the current PR in your terminal:

```bash
claude /pr-review
```

Or specify a PR:

```bash
claude "/pr-review owner/repo#123"
```

## Automated Reviews (Webhook)

### 1. Setup Smee.io (for local development)

```bash
# Install smee client
npm install -g smee-client

# Create a channel at https://smee.io/new
# Copy the webhook URL
```

### 2. Configure GitHub Webhook

1. Go to your repo → Settings → Webhooks → Add webhook
2. Set:
   - **Payload URL**: Your smee.io URL
   - **Content type**: `application/json`
   - **Secret**: Same as `GITHUB_WEBHOOK_SECRET` in `.env`
   - **Events**: Select "Pull requests" and "Issue comments"

### 3. Start the Services

> **Important:** Both services must be running for automated reviews to work!

**Terminal 1** - Smee proxy (forwards GitHub webhooks to localhost):
```bash
smee -u https://smee.io/YOUR_CHANNEL -t http://localhost:3000
```

**Terminal 2** - Webhook listener (receives events and triggers Claude):
```bash
uv run python webhook_listener.py
```

You should see:
```
🤖 AI PR Review - Local Webhook Listener
📡 Listening on http://localhost:3000
⏳ Waiting for webhook events...
```

### 4. Trigger Reviews

Reviews trigger automatically when you:
- Open a new PR
- Push commits to an existing PR
- Comment "hey ai review" on a PR

## Review Output

The AI posts a comment with:

- **Summary**: What the PR does
- **Recommendation**: Approve / Request Changes / Comment
- **Findings** by severity:
  - Critical (security vulnerabilities, breaking bugs)
  - High (significant issues)
  - Medium (code smells)
  - Low/Info (suggestions)
- **What's Good**: Positive aspects of the PR

## Configuration

### Allowed Tools

Edit `.claude/settings.json` to modify permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(gh pr *)",
      "Bash(gh api *)",
      "Read",
      "Grep",
      "Glob"
    ]
  }
}
```

### Review Categories

The skill reviews for:
- **Code Quality** (always): Logic errors, complexity, error handling
- **Security** (always): Injection vulnerabilities, auth flaws, secrets

Optional (add flags to your comment):
- `+perf`: Performance issues
- `+style`: Code style and formatting
- `+docs`: Documentation quality
- `+tests`: Test coverage

Example: "hey ai review +perf +tests"

## Troubleshooting

### "Credit balance is too low"

The webhook is using an API key instead of your Claude subscription. Ensure `ANTHROPIC_API_KEY` is NOT set in your environment when running the listener.

### Review runs but doesn't post comment

Check that:
1. `gh` CLI is authenticated: `gh auth status`
2. Permissions are set in `.claude/settings.json`
3. Docker is running (for MCP server)

### Webhook signature invalid

Ensure `GITHUB_WEBHOOK_SECRET` in `.env` matches the secret configured in GitHub webhook settings.

## Project Structure

```
ai-review/
├── .claude/
│   ├── settings.json      # MCP and permissions config
│   └── skills/
│       └── pr-review/
│           └── SKILL.md   # PR review skill definition
├── webhook_listener.py    # Local webhook server
├── .env                   # Environment variables (not committed)
├── .envrc                 # direnv configuration
└── .gitignore
```

## License

MIT