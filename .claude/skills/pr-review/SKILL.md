---
name: pr-review
description: Review a GitHub pull request with parallel lint, security, and code quality agents (Python-optimised)
---

# AI PR Review — Python Multi-Agent

You are the **orchestrator** for a Python PR review pipeline. You coordinate two specialist agents then synthesize their reports into a single unified review comment.

## Step 1: Fetch PR Data

Parse `owner/repo#NUMBER` from the input. Use GitHub MCP tools:

1. `get_pull_request` → PR metadata (title, description, author, base/head branch)
2. `get_pull_request_diff` → Full unified diff
3. `list_pull_request_files` → Changed file paths

Store the diff text and file list — you will pass them verbatim to sub-agents.

## Step 2: Launch Two Specialist Agents in Parallel

Use the `Agent` tool to spawn **both agents at the same time** (single message, two tool calls). Pass the full diff and file list to each agent in its prompt.

---

### Agent A — Python Lint Agent

```
You are a Python lint and style expert reviewing a PR diff. Return ONLY a JSON object — no markdown, no explanation.

DIFF:
<<<DIFF>>>

CHANGED FILES:
<<<FILES>>>

First, attempt to run static analysis tools on any changed .py files visible in the diff. Try each command and capture output:
- ruff check --select ALL --output-format=json <file> 2>&1
- mypy <file> --ignore-missing-imports --no-error-summary 2>&1 | head -40

Then manually analyse the diff for:
1. PEP 8: line length >100, whitespace, blank lines between functions/classes
2. Naming: snake_case for functions/vars/modules, PascalCase for classes, UPPER_CASE for constants
3. Imports: stdlib → third-party → local ordering, no wildcard imports, no unused imports
4. Type annotations: missing on public functions/methods, incorrect or overly broad types (e.g. Any)
5. Complexity: functions >25 lines, nested conditionals >3 levels, boolean logic that should be extracted
6. Pythonic style: f-strings preferred over .format()/.%, list/dict comprehensions over loops where readable, context managers for resources
7. Dead code: unreachable branches, variables assigned but never used
8. Docstrings: public functions/classes/modules missing docstrings

Return this exact JSON shape:
{
  "tool_output": {
    "ruff": "<raw output or null>",
    "mypy": "<raw output or null>"
  },
  "findings": [
    {
      "severity": "high|medium|low|info",
      "file": "path/to/file.py",
      "line": 42,
      "rule": "E501|naming|imports|typing|complexity|style|dead_code|docs",
      "message": "Concise description of the issue",
      "suggestion": "Specific fix with a short code example if helpful"
    }
  ],
  "summary": "2-3 sentence summary of overall lint health"
}
```

---

### Agent B — Python Security Agent

```
You are a Python security expert reviewing a PR diff. Return ONLY a JSON object — no markdown, no explanation.

DIFF:
<<<DIFF>>>

CHANGED FILES:
<<<FILES>>>

First, attempt to run security scanning tools on any changed .py files visible in the diff. Try:
- bandit -r <file> -f json -q 2>&1
- safety check 2>&1 | head -20  (if requirements.txt or pyproject.toml changed)

Then manually analyse the diff for:
1. Injection: SQL via string interpolation (use parameterised queries), command injection (shell=True, os.system, subprocess with user input), SSTI
2. Hardcoded secrets: API keys, passwords, tokens, private keys — flag any string that looks like a credential
3. Insecure deserialization: pickle.loads() on untrusted data, yaml.load() without safe Loader
4. Path traversal: os.path.join() or open() with unsanitised user-controlled input
5. SSRF: requests.get/post/put with user-controlled URLs lacking an allowlist
6. Weak crypto: MD5/SHA1 for password hashing, DES/ECB mode, hardcoded IV/salt, random instead of secrets module
7. Authentication gaps: missing auth decorators, JWT alg confusion (alg:none), session fixation
8. Sensitive data in logs or error responses: passwords, tokens, PII, full stack traces returned to clients
9. Dependency risks: new packages added to requirements.txt / pyproject.toml — flag any unrecognised or suspicious entries
10. Race conditions: TOCTOU on files, unsynchronised shared mutable state across threads

Return this exact JSON shape:
{
  "tool_output": {
    "bandit": "<raw output or null>",
    "safety": "<raw output or null>"
  },
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "file": "path/to/file.py",
      "line": 42,
      "cwe": "CWE-89",
      "message": "Concise description of the vulnerability",
      "exploit_scenario": "Brief realistic attack scenario",
      "remediation": "Specific fix with a short code example"
    }
  ],
  "summary": "2-3 sentence summary of overall security posture"
}
```

---

## Step 3: Synthesize and Post Review

Once both agents return their JSON reports, YOU (the orchestrator) perform a code quality pass on the same diff, checking:

- Logic errors and off-by-one bugs
- Error handling: bare `except:`, swallowed exceptions, missing finally blocks
- Resource leaks: unclosed files, DB connections, HTTP sessions — use context managers
- SOLID: single responsibility violations, god functions, tight coupling
- Test coverage: are new public functions accompanied by tests?

Then synthesize all three sources (lint report, security report, your quality review):

1. Deduplicate overlapping findings
2. Escalate severity if two or more agents flag the same issue
3. Determine recommendation: **Request Changes** if any Critical/High exist, **Approve** if only Medium/Low/Info, **Comment** if informational only

Post a single review comment via GitHub MCP `create_issue_comment` with this format:

---

```markdown
## 🤖 AI Code Review — Python Multi-Agent

### Summary
[2–3 sentences: PR purpose, what was changed, overall quality verdict]

### Recommendation
[**Approve** | **Request Changes** | **Comment**]

---

### 🔒 Security Findings
> Analysed by Security Agent · Bandit · Manual review

#### Critical
[findings with file:line references, or "None found"]

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### 🧹 Lint & Style Findings
> Analysed by Lint Agent · Ruff · Mypy

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### 🏗️ Code Quality Findings
> Analysed by Orchestrator

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### ✅ What's Good
- [positive point 1]
- [positive point 2]
- [positive point 3]

---

<details>
<summary>🔧 Raw Tool Output</summary>

**Ruff:**
\`\`\`
[output or "not available in this environment"]
\`\`\`

**Mypy:**
\`\`\`
[output or "not available in this environment"]
\`\`\`

**Bandit:**
\`\`\`
[output or "not available in this environment"]
\`\`\`
</details>

---
*Reviewed by Claude AI — Lint Agent + Security Agent + Orchestrator · [`/pr-review`]*
```

---

## Severity Levels

| Level | Meaning |
|-------|---------|
| **Critical** | Exploitable security vulnerability or guaranteed runtime crash |
| **High** | Significant bug or security issue — must fix before merging |
| **Medium** | Code smell, missing type safety, moderate concern |
| **Low** | Minor style, suggestions |
| **Info** | FYI, optional improvement |

## Finding Format

```
- `path/to/file.py:42` — **[Rule / CWE]** Short title
  Why: explanation of the problem
  Fix: `corrected_code_snippet_or_pattern`
```

## Usage

```
/pr-review owner/repo#123
/pr-review owner/repo#123 +perf    # also include performance analysis
```
