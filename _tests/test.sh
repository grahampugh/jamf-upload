#!/bin/bash

# JamfUploader tests

# this folder
DIR=$(dirname "$0")

# which test?
test_type="$1"
verbosity="$2"
url="$3"

# other variables
prefs="$HOME/Library/Preferences/com.github.autopkg.plist"
# prefs="/Users/Shared/com.github.autopkg.plist"

if [[ ! $verbosity ]]; then
    verbosity="-v"
fi

if [[ $url ]]; then
    usual_url=$(defaults read "$prefs" JSS_URL)
    defaults write "$prefs" JSS_URL "$url"
fi

if [[ $test_type == "category" ]]; then
    # upload a category
    "$DIR"/../jamf-upload.sh category \
        --prefs "$prefs" \
        --name JamfUploadTest \
        --priority 18 \
        "$verbosity" \
        "$jss_url" \
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
        "$jss_url" \
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
        "$jss_url" \
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
        "$jss_url" \
        --replace

elif [[ $test_type == "policy" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Authy Desktop" \
        --template "PolicyTemplate-trigger.xml" \
        --key POLICY_NAME="Install Authy Desktop" \
        --key TRIGGER_NAME="Authy Desktop-install" \
        --key CATEGORY="JamfUploadTest" \
        --key pkg_name="Authy Desktop-1.8.4.pkg" \
        "$verbosity" \
        "$jss_url" \
        --replace

elif [[ $test_type == "policy_delete" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy_delete \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Firefox" \
        "$verbosity" \
        "$jss_url"

elif [[ $test_type == "policy_flush" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy_flush \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "0001 - Install Rosetta 2" \
        --interval "Zero Days" \
        "$verbosity" \
        "$jss_url"

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
        "$jss_url" \
        --replace

elif [[ $test_type == "package" || $test_type == "pkg" ]]; then
    # upload a package
    "$DIR"/../jamf-upload.sh pkg \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --pkg "$HOME/Library/AutoPkg/Cache/com.github.nzmacgeek.pkg.authy/Authy Desktop-1.8.4.pkg" \
        --category JamfUploadTest \
        "$verbosity" \
        "$jss_url" \
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
        "$jss_url" \
        --replace

elif [[ $test_type == "patch" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh patch \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Google Chrome" \
        --title "Google Chrome" \
        --policy-name "Install Latest Google Chrome" \
        --template "PatchTemplate-selfservice.xml" \
        --pkg_name "Google Chrome-91.0.4472.77.pkg" \
        --version "91.0.4472.77" \
        "$verbosity" \
        "$jss_url" \
        --replace


elif [[ $test_type == "dock" ]]; then
    # upload a dock item
    "$DIR"/../jamf-upload.sh dock \
        --prefs "$prefs" \
        --name "ETH Self Service" \
        --type "App" \
        --path "/Applications/ETH Self Service.app/" \
        "$verbosity" \
        "$jss_url" \
        --replace

elif [[ $test_type == "slack" ]]; then
    # send a webhook to slack
    "$DIR"/../jamf-upload.sh slack \
        --prefs "$prefs" \
        --name "JamfUploaderSlacker Test - please ignore" \
        --policy-name "JamfUploaderSlacker Test" \
        --policy-category "Applications" \
        --pkg-category "Packages" \
        --pkg-name "Test-Package.pkg" \
        --version "1.2.3" \
        --pkg-uploaded \
        --policy-uploaded \
        --slack-user "JamfUploader Test User" \
        --icon "https://resources.jamf.com/images/logos/Jamf-Icon-color.png" \
        "$verbosity" \
        "$jss_url" \
        --replace

elif [[ $test_type == "teams" ]]; then
    # send a webhook to slack
    "$DIR"/../jamf-upload.sh teams \
        --prefs "$prefs" \
        --name "JamfUploaderTeamsNotifier Test - please ignore" \
        --policy-name "JamfUploaderTeamsNotifier Test" \
        --policy-category "Applications" \
        --pkg-category "Packages" \
        --pkg-name "Test-Package.pkg" \
        --version "1.2.3" \
        --pkg-uploaded \
        --policy-uploaded \
        --teams-user "JamfUploader Test User" \
        --icon "https://resources.jamf.com/images/logos/Jamf-Icon-color.png" \
        "$verbosity" \
        "$jss_url" \
        --replace

else
    echo "Usage: test.sh [test_type]"
fi

# revert url
if [[ $usual_url ]]; then
    defaults write "$prefs" JSS_URL "$usual_url"
fi