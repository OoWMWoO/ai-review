# AI PR Review

Automated GitHub PR code reviews powered by Claude Code. Reviews are triggered automatically when a PR is opened or updated, or on demand via a comment.

## How It Works

```
GitHub PR event
    ↓  (webhook)
Smee.io proxy  →  localhost:3000  →  webhook_listener.py
                                          ↓
                                   claude --print /pr-review
                                          ↓
                                   gh pr view / gh pr diff
                                          ↓
                                   AI analysis (fast or multi-agent)
                                          ↓
                                   gh pr comment → GitHub PR
```

Reviews are posted as a comment on the PR with security findings, lint issues, code quality analysis, and an Approve / Request Changes recommendation.

## Prerequisites

| Tool | Purpose |
|------|---------|
| [Claude Code CLI](https://claude.ai/claude-code) | Runs the review skill — must be logged in |
| [GitHub CLI](https://cli.github.com/) (`gh`) | Fetches PR data and posts comments — must be authenticated |
| [Python 3.13+](https://python.org) + [uv](https://github.com/astral-sh/uv) | Runs the webhook listener |
| [smee-client](https://github.com/probot/smee-client) | Proxies GitHub webhooks to localhost |

Docker is **not required**.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/OoWMWoO/ai-review.git
cd ai-review
uv sync
```

### 2. Authenticate tools

```bash
# Claude Code — log in with your Claude subscription
claude login

# GitHub CLI — authenticate
gh auth login
```

### 3. Configure environment

Create a `.env` file:

```bash
# Webhook signature secret — generate with: openssl rand -hex 32
GITHUB_WEBHOOK_SECRET=your_secret_here
```

> `ANTHROPIC_API_KEY` must NOT be set — the listener deliberately removes it so Claude uses your subscription instead of the API (which costs credits).

### 4. Set up GitHub webhook

1. Go to your repo → **Settings → Webhooks → Add webhook**
2. Configure:
   - **Payload URL**: your Smee.io channel URL (create one free at [smee.io/new](https://smee.io/new))
   - **Content type**: `application/json`
   - **Secret**: same value as `GITHUB_WEBHOOK_SECRET`
   - **Events**: `Pull requests` + `Issue comments`

### 5. Install smee client

```bash
npm install -g smee-client
```

## Running

Both services must be running at the same time.

**Terminal 1** — forward GitHub webhooks to localhost:
```bash
smee -u https://smee.io/YOUR_CHANNEL -t http://localhost:3000
```

**Terminal 2** — start the webhook listener:
```bash
uv run python webhook_listener.py
```

You should see:
```
  ai-review  webhook listener  ·  http://localhost:3000

  forward events:  smee -u $SMEE_URL -t http://localhost:3000

  22:00:00   ready    listening on :3000
```

## Triggering a Review

### Automatic
Reviews run automatically when you:
- Open a new PR
- Push new commits to an existing PR
- Reopen a PR

### On demand
Comment on any PR:
```
hey ai review
```

## Review Output

The AI posts a comment to the PR:

```markdown
## 🤖 AI Code Review — Python Multi-Agent

### Summary
...

### Recommendation
**Approve** | **Request Changes** | **Comment**

### 🔒 Security Findings
### 🧹 Lint & Style Findings
### 🏗️ Code Quality Findings
### ✅ What's Good
```

### Review modes

| PR size | Mode | Time |
|---------|------|------|
| ≤ 8 Python files, < 400 diff lines | Fast — single-pass review | ~2–3 min |
| Larger PRs | Full — specialist agent + orchestrator | ~5–8 min |

## Terminal Logs

```
  22:01:34   event    received  issue_comment
  22:01:34   auth     signature ok
  22:01:34   event    issue_comment:triggered  ·  OoWMWoO/ai-review#3
  22:01:34   start    OoWMWoO/ai-review#3
  22:02:34   wait     OoWMWoO/ai-review#3  still running  (1m elapsed)
  22:03:51   done     OoWMWoO/ai-review#3  (2.3m)
```

## Troubleshooting

**No `event` lines appear when a PR is opened/commented**
- Check smee is running and forwarding to the correct port
- Verify the GitHub webhook is pointed at your Smee URL
- Check the webhook delivery log in GitHub (repo → Settings → Webhooks → Recent Deliveries)

**`auth  rejected — invalid webhook signature`**
- `GITHUB_WEBHOOK_SECRET` in `.env` doesn't match the secret in GitHub webhook settings

**`error  claude CLI not found`**
- Run `claude --version` to confirm it's installed and on PATH

**Review runs but no comment appears on GitHub**
- Run `gh auth status` — must be authenticated
- Check `gh pr comment` works manually: `gh pr comment 1 --repo owner/repo --body "test"`

**`timeout  exceeded 15m limit`**
- PR is very large — increase `timeout=900` in `webhook_listener.py`

**"Credit balance is too low"**
- `ANTHROPIC_API_KEY` is set in your environment — remove it so Claude uses subscription auth

## Project Structure

```
ai-review/
├── .claude/
│   ├── settings.json          # Tool permissions
│   └── skills/
│       └── pr-review/
│           └── SKILL.md       # Review skill — edit to customise analysis
├── webhook_listener.py        # Webhook server and Claude orchestration
├── .env                       # Secrets (not committed)
├── .envrc                     # direnv config
└── pyproject.toml
```

## License

MIT
