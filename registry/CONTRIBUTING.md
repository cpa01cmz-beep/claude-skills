# Contributing to the Claude Skills Registry

Share your skill with the community. This guide walks through submitting a skill
hosted in your own public GitHub repository.

## Requirements

Your skill must:

1. Be hosted in a **public GitHub repository**
2. Have a `SKILL.md` at the repo root (or at the path you declare)
3. Be usable with at least one supported tool (Claude Code, Codex, Gemini CLI, …)

## Submission steps

### 1. Fork this repository

### 2. Create your submission folder

```
registry/skills/<your-github-username>__<skill-name>/
```

The folder name uses a **double underscore** (`__`) to separate your GitHub
username from the skill name. Both halves must match `author` and `name` in your
`metadata.json`.

### 3. Add the required files

#### `metadata.json`

```json
{
  "name": "my-skill",
  "author": "your-github-username",
  "description": "A short description of what your skill does",
  "repository": "https://github.com/your-username/your-repo",
  "path": "",
  "version": "1.0.0",
  "category": "productivity",
  "tags": ["tag1", "tag2"],
  "license": "MIT",
  "adapters": ["claude-code"],
  "icon": false,
  "banner": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill name (lowercase, hyphens) |
| `author` | Yes | Your GitHub username |
| `description` | Yes | What the skill does (10–300 chars) |
| `repository` | Yes | Public GitHub repo URL (`https://github.com/...`) |
| `path` | No | Subdirectory in the repo where `SKILL.md` lives (default: root) |
| `version` | Yes | Semver version |
| `category` | Yes | One of the allowed categories (below) |
| `tags` | Yes | 1–10 lowercase-hyphen tags |
| `license` | Yes | SPDX license identifier |
| `model` | No | Preferred model identifier |
| `adapters` | No | Supported tools (e.g. `claude-code`, `codex`, `gemini-cli`) |
| `icon` | No | `true` if `icon.png` (256×256) is included |
| `banner` | No | `true` if `banner.png` (1200×630) is included |

**Categories:** `development`, `data-engineering`, `devops`, `security`,
`compliance`, `documentation`, `testing`, `research`, `productivity`, `finance`,
`leadership`, `product`, `marketing`, `project-management`, `business-growth`,
`commercial`, `operations`, `design`, `knowledge`, `customer-support`,
`creative`, `education`, `other`.

#### `README.md`

A markdown description of your skill — what it does, key capabilities, example
usage. Shown on the registry.

#### `icon.png` / `banner.png` (optional)

A 256×256 icon and/or 1200×630 banner. Set the matching boolean in
`metadata.json` to `true` when included.

### 4. Validate locally (optional but recommended)

```bash
python registry/scripts/validate.py --clone registry/skills/<author>__<name>/
```

### 5. Open a pull request

CI will automatically:

- Validate `metadata.json` against the schema
- Check the folder name matches `<author>__<name>`
- Verify `README.md` exists and is non-empty
- Clone your repository and verify `SKILL.md` exists at the declared path
- Confirm the committed `index.json` is in sync

## Updating your skill

Open a new PR modifying your folder and bump `version` in `metadata.json`.

## Questions?

Open an issue or discussion in this repository.
