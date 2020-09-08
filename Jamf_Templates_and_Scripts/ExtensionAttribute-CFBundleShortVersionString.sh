#!/bin/sh
CFBundleShortVersionString=""
if [ -f "/Applications/%JSS_INVENTORY_NAME%/Contents/Info.plist" ]; then
    CFBundleShortVersionString=$(defaults read "/Applications/%JSS_INVENTORY_NAME%/Contents/Info.plist" CFBundleShortVersionString)
fi
echo "<result>$CFBundleShortVersionString</result>"
exit 0