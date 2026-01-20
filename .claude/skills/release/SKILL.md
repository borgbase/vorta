---
name: release
description: Guides through the complete Vorta release process - version bump, translations, git tag, GitHub release, PyPi, and macOS builds. Invoke with /release.
---

# Vorta Release Workflow

Guide the user through all release steps interactively. Confirm before each destructive operation.

## Phase 1: Pre-checks

Before starting, verify the repository is ready:

```bash
git status  # Must be clean, on master branch
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

### 2.3 Update translations

```bash
op run -- make translations-update
```

### 2.4 Update metadata and create commit + tag

This uses `make bump-version` which:
- Updates `src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml` with version and date
- Creates commit: "Bump version to vX.Y.Z"
- Creates annotated tag: vX.Y.Z

```bash
make bump-version
```

The tag message should include a brief summary. Prompt the user for input.

## Phase 3: Push to Upstream

```bash
git push upstream master
git push upstream vX.Y.Z
```

## Phase 4: Wait for CI

Monitor the test workflow:

```bash
gh run list --workflow=test.yml --limit=1
gh run watch
```

Wait for tests to pass before proceeding. If tests fail, stop and notify the user.

## Phase 5: Create GitHub Release

### 5.1 Generate changelog

```bash
make changelog
```

Format the output as a bullet list for release notes.

### 5.2 Create draft release

```bash
gh release create vX.Y.Z --draft --title "vX.Y.Z" --notes "CHANGELOG_HERE"
```

Show the user the draft URL for review.

## Phase 6: PyPi Release

```bash
op run -- make pypi-release
```

This builds the sdist and uploads to PyPi via twine.

## Phase 7: macOS Builds

### 7.1 Trigger both architecture builds

Default Borg version: 1.4.3 (ask user if they want different)

```bash
# ARM build (Apple Silicon)
gh workflow run build-macos.yml -f branch=master -f macos_version=macos-14 -f borg_version=1.4.3

# Intel build
gh workflow run build-macos.yml -f branch=master -f macos_version=macos-15-intel -f borg_version=1.4.3
```

### 7.2 Wait for builds to complete

```bash
# List recent workflow runs to get run IDs
gh run list --workflow=build-macos.yml --limit=2

# Watch both runs (run these commands and wait)
gh run watch <arm-run-id>
gh run watch <intel-run-id>
```

### 7.3 Download artifacts

```bash
gh run download <arm-run-id> -D ./release-artifacts
gh run download <intel-run-id> -D ./release-artifacts
```

### 7.4 Upload to GitHub release

```bash
gh release upload vX.Y.Z ./release-artifacts/Vorta-v*-arm.dmg ./release-artifacts/Vorta-v*-intel.dmg
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

Update the Sparkle appcast for macOS auto-updates:

```bash
make update-appcast
```

## Completion

Summarize what was done:
- Version bumped to vX.Y.Z
- Tag pushed to upstream
- GitHub release published: [link]
- PyPi package uploaded
- macOS DMGs (ARM + Intel) attached to release
- Appcast updated for auto-updates
