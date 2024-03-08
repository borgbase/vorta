#!/usr/bin/env bash
# Inspired by https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh

set -eux

APP_BUNDLE_ID="com.borgbase.client.macos"
APP_BUNDLE="Vorta"
# CERTIFICATE_NAME="Developer ID Application: Joe Doe (XXXXXX)"
# APPLE_ID_USER="name@example.com"
# APPLE_ID_PASSWORD="CHANGEME"
# APPLE_TEAM_ID="CNMSCAXT48"


# Sign app bundle, Sparkle and Borg
codesign --verbose --force --sign "$CERTIFICATE_NAME" --timestamp --deep --options runtime \
    $APP_BUNDLE.app/Contents/Frameworks/Sparkle.framework

find $APP_BUNDLE.app/Contents/Resources/borg-dir \
    -type f \( -name \*.so -or -name \*.dylib -or -name borg.exe -or -name Python \) \
    -exec codesign --verbose --force --timestamp --deep --sign "${CERTIFICATE_NAME}" \
    --entitlements ../package/entitlements.plist  --options runtime {} \;

codesign --verify --force --verbose --deep \
        --options runtime --timestamp \
        --entitlements ../package/entitlements.plist \
        --sign "$CERTIFICATE_NAME" $APP_BUNDLE.app


# Create DMG
rm -rf $APP_BUNDLE.dmg
create-dmg \
  --volname "Vorta Installer" \
  --window-size 410 300 \
  --icon-size 100 \
  --icon "Vorta.app" 70 150 \
  --hide-extension "Vorta.app" \
  --app-drop-link 240 150 \
  "Vorta.dmg" \
  "Vorta.app"

# Notarize DMG
xcrun notarytool submit \
    --output-format plist --wait --timeout 10m \
    --apple-id $APPLE_ID_USER \
    --password $APPLE_ID_PASSWORD \
    --team-id $APPLE_TEAM_ID \
    "$APP_BUNDLE.dmg"

# Staple the notary ticket
xcrun stapler staple $APP_BUNDLE.dmg
xcrun stapler staple $APP_BUNDLE.app
xcrun stapler validate $APP_BUNDLE.dmg
