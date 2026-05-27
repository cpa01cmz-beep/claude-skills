# example-skill

This is a **template submission** that shows the shape of a community entry in
the claude-skills registry. Use it as a starting point for your own skill.

## How to submit your own

1. Copy this folder to `registry/skills/<your-github-username>__<your-skill-name>/`
2. Edit `metadata.json`:
   - `name` / `author` must match the folder name (`<author>__<name>`)
   - `repository` must be a public GitHub repo that contains a `SKILL.md`
   - `path` is the subdirectory within that repo where `SKILL.md` lives (omit or `""` for the repo root)
3. Replace this `README.md` with a description of your skill
4. Open a pull request

CI validates your `metadata.json` against the schema, checks the folder name,
and (in the validate workflow) clones your repo to confirm `SKILL.md` exists.

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for the full guide.
