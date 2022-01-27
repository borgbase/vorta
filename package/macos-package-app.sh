#!/usr/bin/env bash
# Inspired by https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh

set -eux

APP_BUNDLE_ID="com.borgbase.client.macos"
APP_BUNDLE="Vorta"
# CERTIFICATE_NAME="Developer ID Application: Joe Doe (XXXXXX)"
# APPLE_ID_USER="name@example.com"
# APPLE_ID_PASSWORD="@keychain:Notarization"


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
RESULT=$(xcrun altool --notarize-app --type osx \
    --primary-bundle-id $APP_BUNDLE_ID \
    --username $APPLE_ID_USER --password $APPLE_ID_PASSWORD \
    --file "$APP_BUNDLE.dmg" --output-format xml)

REQUEST_UUID=$(echo "$RESULT" | xpath5.18 "//key[normalize-space(text()) = 'RequestUUID']/following-sibling::string[1]/text()" 2> /dev/null)

# Poll for notarization status
echo "Submitted notarization request $REQUEST_UUID, waiting for response..."
sleep 60
while true
do
  RESULT=$(xcrun altool --notarization-info "$REQUEST_UUID" \
    --username "$APPLE_ID_USER" \
    --password "$APPLE_ID_PASSWORD" \
    --output-format xml)
  STATUS=$(echo "$RESULT" | xpath5.18 "//key[normalize-space(text()) = 'Status']/following-sibling::string[1]/text()" 2> /dev/null)

  if [ "$STATUS" = "success" ]; then
    echo "Notarization of $APP_BUNDLE succeeded!"
    break
  elif [ "$STATUS" = "in progress" ]; then
    echo "Notarization in progress..."
    sleep 20
  else
    echo "Notarization of $APP_BUNDLE failed:"
    echo "$RESULT"
    exit 1
  fi
done

# Staple the notary ticket
xcrun stapler staple $APP_BUNDLE.dmg
xcrun stapler staple $APP_BUNDLE.app
xcrun stapler validate $APP_BUNDLE.dmg
