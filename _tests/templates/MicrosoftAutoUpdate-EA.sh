#!/bin/bash
MAUVersion="None"
if [ -f "/Library/Application Support/Microsoft/MAU2.0/Microsoft AutoUpdate.app/Contents/Info.plist" ]; then
    MAUVersion=$(/usr/bin/defaults read "/Library/Application Support/Microsoft/MAU2.0/Microsoft AutoUpdate.app/Contents/Info.plist" CFBundleVersion)
fi

echo "<result>$MAUVersion</result>"

exit 0