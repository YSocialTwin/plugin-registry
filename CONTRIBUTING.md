# Adding a plugin

1. **Make your plugin installable.** Its repository must be public and contain
   `meta/info.json` (name, description, authors, category). A plugin that adds features to
   YSocial also declares them in `meta/registry.json`; see *Developing plugins* in the
   YSocial documentation. Choose the install recipe that fits: `requirements`
   (`pip install -r requirements.txt`), `pip-editable` (`pip install -e .`) or `auto`.
2. **Add one object to `registry.json`** (copy [`examples/registry.example.json`](examples/registry.example.json)),
   keeping the list sorted by `id`.
3. **Run the checks locally:**
   ```bash
   python scripts/validate_registry.py --check-repos
   ```
4. **Open a pull request.** CI runs the same checks. A maintainer reviews the repository
   before merging. New plugins start as `community`; moving a plugin to `official` means
   moving its repository to the `YSocialTwin` organisation.
5. After merge, YSocial installations pick the plugin up the next time they start.

## Review criteria

* The repository is public, licensed and does what its description says.
* No obfuscated code, no download-and-run of remote scripts at install time.
* Dependencies are declared (`requirements.txt` / `pyproject.toml`) and compatible with the
  YSocial core (YSocial installs plugins with the core's versions pinned).
* It installs and validates from the YSocial plugin page on a clean installation.

## Changing or removing an entry

Open a pull request. Removing an entry only hides the plugin from the list; plugins already
installed keep working.

## Built-in plugins (maintainers)

`builtin.json` describes the plugins released together with YSocial. Edit it here (never in YSocial),
run `python scripts/validate_registry.py`, merge, then in YSocial run
`python scripts/packaging/sync_builtin_plugins.py --ref <commit>` and release. Install commands in
this file must be `python -m pip install ...`; validation files are paths relative to the plugin.
