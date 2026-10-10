---
name: release
description: Guides through the complete Vorta release process - version bump, translations, git tag, GitHub release, PyPi, and macOS builds. Invoke with /release.
---

# Vorta Release Workflow

Guide the user through all release steps interactively. Confirm before each destructive operation.

## Phase 1: Pre-checks

Before starting, verify the repository is ready:

```bash
make release-preflight  # Clean tree, no staged changes, on master
```

If there are uncommitted changes, stop and ask the user to resolve them first.

## Phase 2: Version Bump

### 2.1 Get the new version number

Ask the user for the new version number (e.g., `0.12.0`). Verify it follows semver format.

### 2.2 Update version file

Edit `src/vorta/_version.py`:
```python
__version__ = "X.Y.Z"  # New version
```

### 2.3 Update translations (optional)

```bash
make translations-from-source  # extract strings, merge into every .ts
make translations-to-qm        # compile .qm files
```

This runs `pylupdate6` locally; no 1Password needed. New strings arrive as
`type="unfinished"` — use `/translate review <lang>` to fill them in, or ship them
untranslated (they fall back to English).

### 2.4 Update metadata and create commit + tag

Note: there is no `make bump-version` target — these steps live here instead.

**Important:** add a *new* `<release>` entry at the top of `<releases>`. Do not
rewrite the existing ones; the version history is consumed by AppStream/Flatpak.

1. Update appdata.xml with new version and today's date:
```bash
# Edit src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
# Change: <release version="vX.Y.Z" date="YYYY-MM-DD" ...>
```

2. Create commit and tag:
```bash
git add src/vorta/_version.py src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
git commit -m "Bump version to vX.Y.Z"
git tag -a vX.Y.Z -m "TAG_MESSAGE_HERE"
```

Prompt the user for the tag message (brief summary of changes).

## Phase 3: Push to Upstream

```bash
git push upstream master
git push upstream vX.Y.Z
```

## Phase 4: Wait for CI

Monitor the test workflow:

```bash
gh run list --workflow=test.yml --limit=1
gh run watch <run-id> --exit-status
```

Wait for tests to pass before proceeding. If tests fail, stop and notify the user.

## Phase 5: Create GitHub Release

### 5.1 Generate changelog

```bash
make changelog
```

Format the output as a bullet list for release notes, excluding:
- Version bump commits
- CI-only changes
- Minor dev tooling updates

### 5.2 Create draft release

```bash
gh release create vX.Y.Z --draft --title "vX.Y.Z" --notes "CHANGELOG_HERE"
```

Show the user the draft URL for review.

## Phase 6: PyPi Release

Note: Use `command op` to bypass shell function issues with 1Password CLI.

```bash
command op run -- make pypi-release
```

This builds the sdist and uploads to PyPi via twine.

If `op` fails, provide manual instructions:
```bash
uv run python -m build --sdist
uv run twine upload dist/vorta-X.Y.Z.tar.gz
```

## Phase 7: macOS Builds

### 7.1 Trigger both architecture builds

Default Borg version: 1.4.4 (ask user if they want different)

There is no `branch` input — dispatch against the tag with `--ref` so the DMG is
built from exactly what was tagged. Runner choices are `macos-26`, `macos-26-intel`,
`macos-15`, `macos-15-intel`.

```bash
# ARM build (Apple Silicon)
gh workflow run build-macos.yml --ref vX.Y.Z -f macos_version=macos-15 -f borg_version=1.4.4

# Intel build (x86_64 runner)
gh workflow run build-macos.yml --ref vX.Y.Z -f macos_version=macos-15-intel -f borg_version=1.4.4
```

### 7.2 Wait for builds to complete

```bash
# List recent workflow runs to get run IDs
gh run list --workflow=build-macos.yml --limit=2

# Watch both runs
gh run watch <arm-run-id> --exit-status
gh run watch <intel-run-id> --exit-status
```

### 7.3 Download artifacts

```bash
rm -rf ./release-artifacts && mkdir -p ./release-artifacts
gh run download <arm-run-id> -D ./release-artifacts
gh run download <intel-run-id> -D ./release-artifacts
```

### 7.4 Upload to GitHub release

Note: Artifacts are in nested directories (e.g., `./release-artifacts/Vorta-vX.Y.Z-arm.dmg/Vorta-vX.Y.Z-arm.dmg`)

```bash
gh release upload vX.Y.Z \
  "./release-artifacts/Vorta-vX.Y.Z-arm.dmg/Vorta-vX.Y.Z-arm.dmg" \
  "./release-artifacts/Vorta-vX.Y.Z-intel.dmg/Vorta-vX.Y.Z-intel.dmg"
```

### 7.5 Cleanup

```bash
rm -rf ./release-artifacts
```

## Phase 8: Publish Release

After verifying the release looks correct:

```bash
gh release edit vX.Y.Z --draft=false
```

Provide the release URL to the user.

## Phase 9: Update GitHub Pages (Appcast)

Update the Sparkle appcast for macOS auto-updates.

Note: The gh-pages branch doesn't have pre-commit config, so commits may fail. Handle this:

```bash
make update-appcast
```

If the commit fails due to pre-commit, complete manually:
```bash
# If already on gh-pages from failed make target:
PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "Update appcast for vX.Y.Z"
git push upstream gh-pages
git checkout master
```

## Completion

Summarize what was done:
- Version bumped to vX.Y.Z
- Tag pushed to upstream
- GitHub release published: [link]
- PyPi package uploaded
- macOS DMGs (ARM + Intel) attached to release
- Appcast updated for auto-updates
