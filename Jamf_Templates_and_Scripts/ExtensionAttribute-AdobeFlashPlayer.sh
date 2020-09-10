#!/bin/bash
FlashVersion=""
if [ -f "/Library/Internet Plug-Ins/Flash Player.plugin/Contents/Info.plist" ]; then
	FlashVersion=$(defaults read /Library/Internet\ Plug-Ins/Flash\ Player.plugin/Contents/Info.plist CFBundleShortVersionString)
fi

echo "<result>$FlashVersion</result>"

exit 0
