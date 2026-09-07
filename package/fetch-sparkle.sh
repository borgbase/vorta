#!/usr/bin/env bash
# Fetch Sparkle.framework from the upstream release.
# Homebrew's `sparkle` cask was disabled on 2026-09-01 because the demo app it bundles
# fails the Gatekeeper check. The framework itself is fine and we re-sign it in
# package/macos-package-app.sh, so we take it straight from the upstream tarball.
set -euo pipefail

SPARKLE_VERSION="${SPARKLE_VERSION:-2.9.6}"
SPARKLE_SHA256="${SPARKLE_SHA256:-52bf9e88cdd972fc0c81501377a880e90d47031bd8ca5462488f843e2609e192}"
DEST="${1:?usage: fetch-sparkle.sh <Frameworks directory>}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

TARBALL="$WORK/Sparkle-$SPARKLE_VERSION.tar.xz"
curl -fsSL -o "$TARBALL" \
  "https://github.com/sparkle-project/Sparkle/releases/download/${SPARKLE_VERSION}/Sparkle-${SPARKLE_VERSION}.tar.xz"
echo "${SPARKLE_SHA256}  ${TARBALL}" | shasum -a 256 -c -

tar -xJf "$TARBALL" -C "$WORK"
FRAMEWORK=$(find "$WORK" -maxdepth 2 -type d -name Sparkle.framework -print -quit)
[ -n "$FRAMEWORK" ] || { echo "Sparkle.framework not found in Sparkle-${SPARKLE_VERSION}.tar.xz" >&2; exit 1; }

mkdir -p "$DEST"
rm -rf "$DEST/Sparkle.framework"
cp -R "$FRAMEWORK" "$DEST/"
xattr -cr "$DEST/Sparkle.framework"
