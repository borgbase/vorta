#!/usr/bin/env bash
# Inspired by https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh

set -e

CERTIFICATE_NAME="Developer ID Application: Manuel Riel (CNMSCAXT48)"
APP_BUNDLE_ID="com.borgbase.client.macos"
APP_BUNDLE="Vorta"
APPLE_ID_USER="manu@snapdragon.cc"
APPLE_ID_PASSWORD="@keychain:Notarization"

cd dist

# codesign --deep is only 1 level deep. It misses Sparkle embedded app AutoUpdate
codesign --verbose --force --sign "$CERTIFICATE_NAME" --timestamp --deep --options runtime \
    $APP_BUNDLE.app/Contents/Frameworks/Sparkle.framework/Resources/Autoupdate.app

codesign --verify --force --verbose --deep \
        --options runtime --timestamp \
        --entitlements ../package/entitlements.plist \
        --sign "$CERTIFICATE_NAME" $APP_BUNDLE.app

# ditto -c -k --rsrc --keepParent "$APP_BUNDLE.app" "${APP_BUNDLE}.zip"
rm -rf $APP_BUNDLE.dmg
appdmg ../package/appdmg.json $APP_BUNDLE.dmg

RESULT=$(xcrun altool --notarize-app --type osx \
    --primary-bundle-id $APP_BUNDLE_ID \
    --username $APPLE_ID_USER --password $APPLE_ID_PASSWORD \
    --file "$APP_BUNDLE.dmg" --output-format xml)

REQUEST_UUID=$(echo "$RESULT" | xpath \
  "//key[normalize-space(text()) = 'RequestUUID']/following-sibling::string[1]/text()" 2> /dev/null)

# Poll for notarization status
echo "Submitted notarization request $REQUEST_UUID, waiting for response..."
sleep 60
while true
do
  RESULT=$(xcrun altool --notarization-info "$REQUEST_UUID" \
    --username "$APPLE_ID_USER" \
    --password "$APPLE_ID_PASSWORD" \
    --output-format xml)
  STATUS=$(echo "$RESULT" | xpath "//key[normalize-space(text()) = 'Status']/following-sibling::string[1]/text()" 2> /dev/null)

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