#!/bin/sh
CFBundleVersion=""
if [ -f "/Applications/%JSS_INVENTORY_NAME%/Contents/Info.plist" ]; then
    CFBundleVersion=$(defaults read "/Applications/%JSS_INVENTORY_NAME%/Contents/Info.plist" CFBundleVersion)
fi
echo "<result>$CFBundleVersion</result>"
exit 0