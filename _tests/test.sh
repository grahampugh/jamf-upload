#!/bin/bash

# this folder
DIR=$(dirname "$0")

# example commands to run

# upload a category (do not replace)
"$DIR"/../jamf-upload.sh category --prefs ~/Library/Preferences/com.github.autopkg.plist --name JamfUploadTest --priority 18 -vv

# upload a profile (do not replace)
"$DIR"/../jamf-upload.sh profile --prefs ~/Library/Preferences/com.github.autopkg.plist --name "VLC Tests"  --template ProfileTemplate-test-users.xml --payload org.videolan.vlc.plist --identifier org.videolan.vlc --category JamfUploadTest --organization "Graham Pugh Inc." --description "Amazing test profile" --computergroup "Testing" -v

# uplaod a package
"$DIR"/../jamf-upload.sh pkg --prefs ~/Library/Preferences/com.github.autopkg.plist --pkg python_recommended_signed-3.9.5.09222021234106.pkg --category JamfUploadTest -v

