#!/bin/bash

if [[ -f "/Library/Preferences/com.obdev.BlockBlock.plist" ]]; then
    result=$(/usr/libexec/PlistBuddy -c "Print :version" "/Library/Preferences/com.obdev.BlockBlock.plist" 2>/dev/null)
else
    result=""
fi

echo "<result>${result}</result>"
