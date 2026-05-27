# Claude Skills Registry

A browsable, searchable registry of skills — the skill packages that ship in
this repo **plus** community-submitted skills hosted in their own repos.

Modeled on the [gitagent registry](https://registry.gitagent.sh) pattern:
GitHub is the source of truth, there is no database and no backend.

```
PR → CI validates → merge → index.json regenerated → static site reads index.json
```

## What's in here

| Path | Purpose |
|------|---------|
| `schema/metadata.schema.json` | JSON Schema for a community submission's `metadata.json` |
| `scripts/validate.py` | Validate a submission folder (stdlib only) |
| `scripts/build_index.py` | Generate `index.json` from internal + community skills (stdlib only) |
| `skills/<author>__<name>/` | Community submission folders |
| `index.json` | Generated catalog the site reads |
| `site/` | Static browse/search UI (vanilla HTML/CSS/JS, no build step) |

## Two sources, one index

- **Internal** entries are derived automatically from
  [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) — every
  plugin in this repo appears in the registry.
- **Community** entries are folders under `skills/`, each pointing at an external
  public GitHub repo that contains a `SKILL.md`.

## Develop

No npm, no build system — Python standard library only.

```bash
# Regenerate index.json (deterministic, no network)
python registry/scripts/build_index.py

# Enrich entries with live GitHub stars/forks (network)
python registry/scripts/build_index.py --github

# Fail if the committed index.json is stale (used in CI)
python registry/scripts/build_index.py --check

# Validate every community submission
python registry/scripts/validate.py --all

# Validate + clone each repo to confirm SKILL.md exists (network)
python registry/scripts/validate.py --clone registry/skills/<author>__<name>/
```

## Run the site locally

```bash
cd registry
python -m http.server 8000
# open http://localhost:8000/site/
```

The site fetches `index.json`; serve from the `registry/` directory so the
relative path resolves.

## Submit a skill

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT
