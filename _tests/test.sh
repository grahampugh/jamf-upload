#!/bin/bash

# this folder
DIR=$(dirname "$0")

# example commands to run

# upload a category (do not replace)
# "$DIR"/../jamf-upload.sh category --prefs ~/Library/Preferences/com.github.autopkg.plist --name JamfUploadTest --priority 18 -vv

# upload a profile (do not replace)
"$DIR"/../jamf-upload.sh profile \
    --prefs ~/Library/Preferences/com.github.autopkg.plist \
    --name "Carbon Copy Cloner" \
    --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
    --template ProfileTemplate-test-users.xml \
    --payload com.bombich.ccc.plist \
    --identifier com.bombich.ccc \
    --category JamfUploadTest \
    --organization "Graham Pugh Inc." \
    --description "Amazing test profile" \
    --computergroup "Testing" \
    -vv \
    --key REGISTRATION_CODE="FAKE-CODE" \
    --key REGISTRATION_EMAIL="no@yes.com" \
    --key REGISTRATION_NAME="ETH License Administration" \
    --key REGISTRATION_PRODUCT_NAME='Carbon Copy Cloner 6 Volume License' \
    --key replace_profile=True

# uplaod a package
# "$DIR"/../jamf-upload.sh pkg --prefs ~/Library/Preferences/com.github.autopkg.plist --pkg python_recommended_signed-3.9.5.09222021234106.pkg --category JamfUploadTest -v

