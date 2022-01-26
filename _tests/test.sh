#!/bin/bash

# JamfUploader tests

# this folder
DIR=$(dirname "$0")

# which test?
test_type="$1"
verbosity="$2"

# other variables
prefs="$HOME/Library/Preferences/com.github.autopkg.plist"
# prefs="/Users/Shared/com.github.autopkg.plist"

if [[ ! $verbosity ]]; then
    verbosity="-v"
fi

if [[ $test_type == "category" ]]; then
    # upload a category
    "$DIR"/../jamf-upload.sh category \
        --prefs "$prefs" \
        --name JamfUploadTest \
        --priority 18 \
        "$verbosity" \
        --replace

elif [[ $test_type == "group" ]]; then
    # upload a computer group
    "$DIR"/../jamf-upload.sh group \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Firefox test users" \
        --template "SmartGroupTemplate-test-users.xml" \
        --key POLICY_NAME="Firefox" \
        "$verbosity" \
        --replace

elif [[ $test_type == "profile" ]]; then
    # upload a profile
    "$DIR"/../jamf-upload.sh profile \
        --prefs "$prefs" \
        --name "Carbon Copy Cloner" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template ProfileTemplate-test-users.xml \
        --payload com.bombich.ccc.plist \
        --identifier com.bombich.ccc \
        --category JamfUploadTest \
        --organization "Graham Pugh Inc." \
        --description "Amazing test profile" \
        --computergroup "Testing" \
        "$verbosity" \
        --key REGISTRATION_CODE="FAKE-CODE" \
        --key REGISTRATION_EMAIL="yes@yes.com" \
        --key REGISTRATION_NAME="ETH License Administration" \
        --key REGISTRATION_PRODUCT_NAME='Carbon Copy Cloner 6 Volume License' \
        --replace

elif [[ $test_type == "ea" ]]; then
    # upload an extension attribute
    "$DIR"/../jamf-upload.sh ea \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft AutoUpdate Version" \
        --script "MicrosoftAutoUpdate-EA.sh" \
        "$verbosity" \
        --replace

elif [[ $test_type == "policy" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Firefox" \
        --template "PolicyTemplate-trigger.xml" \
        --key POLICY_NAME="Install Firefox" \
        --key TRIGGER_NAME="Firefox-install" \
        --key CATEGORY="JamfUploadTest" \
        --key pkg_name="Firefox-96.0.pkg" \
        "$verbosity" \
        --replace

elif [[ $test_type == "restriction" ]]; then
    # upload a software restriction
    "$DIR"/../jamf-upload.sh restriction \
        --prefs "$prefs" \
        --name "Restrict Carbon Copy Cloner" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template RestrictionTemplate-singlegroup.xml \
        --process_name "Carbon Copy Cloner" \
        --display_message "Carbon Copy Cloner is not allowed." \
        --match_exact_process_name \
        --kill_process \
        --computergroup Testing \
        "$verbosity" \
        --replace

elif [[ $test_type == "package" || $test_type == "pkg" ]]; then
    # upload a package
    "$DIR"/../jamf-upload.sh pkg \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --pkg "$HOME/Downloads/Microsoft_Office_Reset_1.8.pkg" \
        --category JamfUploadTest \
        "$verbosity" \
        --replace
    
elif [[ $test_type == "script" ]]; then
    # upload a script
    "$DIR"/../jamf-upload.sh script \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft Office License Type.sh" \
        --script "Microsoft Office License Type.sh" \
        --script_parameter4 "License Type" \
        "$verbosity" \
        --replace

elif [[ $test_type == "dock" ]]; then
    # upload a dock item
    "$DIR"/../jamf-upload.sh dock \
        --prefs "$prefs" \
        --name "ETH Self Service" \
        --type "App" \
        --path "/Applications/ETH Self Service.app/" \
        "$verbosity" \
        --replace

else
    echo "Usage: test.sh [test_type]"
fi
