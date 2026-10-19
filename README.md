# YSocial plugin registry

The public list of plugins that the YSocial plugin page can install. YSocial reads
[`registry.json`](registry.json) when it starts (and keeps a copy for offline use), so a
plugin listed here becomes available in an **already installed** YSocial, with no new
YSocial or installer release.

Each entry points to a GitHub repository; the registry does not host any code.

## Trust levels

| Level | Meaning | What the user sees |
| --- | --- | --- |
| `official` | Maintained by the YSocial team (repositories of the `YSocialTwin` organisation only) | Installs like the built-in plugins |
| `community` | Anyone else | A "Community" badge, a warning with the repository link and an explicit confirmation before install/update |

`trust: official` is ignored by YSocial for any other owner, so an entry cannot give itself
that status.

## What an entry can and cannot do

* It names a repository (`owner/name`) and a branch. The clone URL is always built by
  YSocial from those two values.
* It picks an install **recipe** by name (`auto`, `requirements`, `pip-editable`); it cannot
  carry commands. Installing still runs the plugin's own code (`pip install` executes
  `setup.py`), which is why community plugins ask for confirmation.
* Malformed entries are skipped by YSocial; plugins that ship with YSocial always win on a
  clash of `id`, repository or directory.

## Add your plugin

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: open a pull request that adds one object
to `registry.json`; CI checks the format and that your repository is reachable and has a
`meta/info.json`.

## Format

[`registry.schema.json`](registry.schema.json) is the JSON Schema; `scripts/validate_registry.py`
applies the same rules YSocial applies (standard library only):

```bash
python scripts/validate_registry.py                # rules
python scripts/validate_registry.py --check-repos  # + repositories exist (uses GITHUB_TOKEN if set)
```

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | unique, `^[a-z][a-z0-9_]{2,47}$` |
| `name` | yes | shown in the plugin list |
| `category` | yes | `agent_extensions`, `frontend_extensions` or `backend_extensions` |
| `repo` | yes | GitHub `owner/name` |
| `description` | no | up to 400 characters (used until the plugin's own `meta/info.json` is installed) |
| `branch` | no | default `main` |
| `directory` | no | folder under `external/`, default the repository name |
| `recipe` | no | `auto` (default: detect `requirements.txt` / `pyproject.toml` / `setup.py`), `requirements`, `pip-editable` |
| `trust` | no | `community` (default) or `official` |
| `min_ysocial_version` | no | older YSocial versions do not list the plugin |
| `authors`, `import_name`, `private` | no | `private: true` plugins are shown only with `--development` until the repository is public |
