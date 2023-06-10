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

if [[ $test_type == "ldap_server" ]]; then
    # upload a category
    "$DIR"/../jamf-upload.sh ldap_server \
        --prefs "$prefs" \
        --name "d.ethz.ch" \
        --template "/Users/gpugh/sourcecode/id-mac-tools/jamf-api-tools/templates/LDAPServerETH.xml" \
        "$verbosity" \
        "$url" \
        --replace

elif [[ $test_type == "category" ]]; then
    # upload a category
    "$DIR"/../jamf-upload.sh category \
        --prefs "$prefs" \
        --name JamfUploadTest \
        --priority 18 \
        "$verbosity" \
        "$url" \
        --replace

elif [[ $test_type == "group" ]]; then
    # upload a computer group
    "$DIR"/../jamf-upload.sh group \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Firefox test users" \
        --template "templates/SmartGroupTemplate-test-users.xml" \
        --key POLICY_NAME="Firefox" \
        "$verbosity" \
        "$url" \
        --replace

# elif [[ $test_type == "profile" ]]; then
#     # upload a profile (payload plist)
#     "$DIR"/../jamf-upload.sh profile \
#         --prefs "$prefs" \
#         --name "Carbon Copy Cloner" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --template "templates/ProfileTemplate-1-group-1-exclusion.xml" \
#         --payload "templates/com.bombich.ccc.plist" \
#         --identifier com.bombich.ccc \
#         --category JamfUploadTest \
#         --organization "Graham Pugh Inc." \
#         --description "Amazing test profile" \
#         --computergroup "Testing" \
#         "$verbosity" \
#         "$url" \
#         --key REGISTRATION_CODE="FAKE-CODE" \
#         --key REGISTRATION_EMAIL="yes@yes.com" \
#         --key REGISTRATION_NAME="ETH License Administration" \
#         --key REGISTRATION_PRODUCT_NAME='Carbon Copy Cloner 6 Volume License' \
#         --key EXCLUSION_GROUP_NAME="Firefox test users" \
#         --replace

# elif [[ $test_type == "profile" ]]; then
#     # upload a profile (mobileconfig)
#     "$DIR"/../jamf-upload.sh profile \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --template "templates/ProfileTemplate-test-users.xml" \
#         --category JamfUploadTest \
#         --computergroup "Testing" \
#         --mobileconfig "templates/TestProfileIdentifiers.mobileconfig" \
#         "$verbosity" \
#         "$url" \
#         --replace

elif [[ $test_type == "profile" ]]; then
    # upload a profile (mobileconfig)
    "$DIR"/../jamf-upload.sh profile \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template "templates/ProfileTemplate-test-users.xml" \
        --category JamfUploadTest \
        --computergroup "Testing" \
        --mobileconfig "templates/MicrosoftAutoUpdate-notifications.mobileconfig" \
        --key PROFILE_NAME="Microsoft AutoUpdate Notifications" \
        --key PROFILE_DESCRIPTION="Enables notifications for Microsoft AutoUpdate" \
        --key ORGANIZATION="Microsoft" \
        "$verbosity" \
        "$url" \
        --replace

elif [[ $test_type == "ea" ]]; then
    # upload an extension attribute
    "$DIR"/../jamf-upload.sh ea \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft AutoUpdate Version" \
        --script "templates/MicrosoftAutoUpdate-EA.sh" \
        "$verbosity" \
        "$url" \
        --replace

# elif [[ $test_type == "macapp" ]]; then
#     # upload a policy
#     "$DIR"/../jamf-upload.sh macapp \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --name "Numbers" \
#         --template "templates/MacApp-allcomputers.xml" \
#         --key CATEGORY="Applications" \
#         --key DEPLOYMENT_TYPE="Make Available in Self Service" \
#         "$verbosity" \
#         "$url" \
#         --replace

elif [[ $test_type == "macapp" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh macapp \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Numbers - auto-install" \
        --clone-from "Numbers" \
        --template "templates/MacApp-noscope-autoinstall.xml" \
        --key CATEGORY="Applications" \
        --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install" \
        "$verbosity" \
        "$url" \
        --replace


elif [[ $test_type == "policy" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Authy Desktop" \
        --template "templates/PolicyTemplate-trigger.xml" \
        --key POLICY_NAME="Install Authy Desktop" \
        --key TRIGGER_NAME="Authy Desktop-install" \
        --key CATEGORY="JamfUploadTest" \
        --key pkg_name="Authy Desktop-1.8.4.pkg" \
        "$verbosity" \
        "$url" \
        --replace

elif [[ $test_type == "policy_delete" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy_delete \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Firefox" \
        "$verbosity" \
        "$url"

elif [[ $test_type == "policy_flush" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh policy_flush \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "0001 - Install Rosetta 2" \
        --interval "Zero Days" \
        "$verbosity" \
        "$url"

# elif [[ $test_type == "account" ]]; then
#     # upload an account
#     "$DIR"/../jamf-upload.sh account \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --name "Test Group" \
#         --type "group" \
#         --template "templates/Account-Group-local.xml" \
#         "$verbosity" \
#         "$url"

# elif [[ $test_type == "account" ]]; then
#     # upload an account
#     "$DIR"/../jamf-upload.sh account \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --name "graham" \
#         --type "user" \
#         --template "templates/Account-User-groupaccess.xml" \
#         --key ACCOUNT_FULLNAME="Graham Pugh Test Account" \
#         --key ACCOUNT_PASSWORD="GrahamsPassword" \
#         --key ACCOUNT_EMAIL="graham@pugh.com" \
#         --key GROUP_NAME="Test Group" \
#         "$verbosity" \
#         "$url"

elif [[ $test_type == "account" ]]; then
    # upload an account
    "$DIR"/../jamf-upload.sh account \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "graham" \
        --type "user" \
        --template "templates/Account-User-fullaccess.xml" \
        --key ACCOUNT_FULLNAME="Graham Pugh Test Account" \
        --key ACCOUNT_EMAIL="graham@pugh.com" \
        "$verbosity" \
        "$url" \
        --replace


elif [[ $test_type == "restriction" ]]; then
    # upload a software restriction
    "$DIR"/../jamf-upload.sh restriction \
        --prefs "$prefs" \
        --name "Restrict Carbon Copy Cloner" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template "templates/RestrictionTemplate-singlegroup.xml" \
        --process_name "Carbon Copy Cloner" \
        --display_message "Carbon Copy Cloner is not allowed." \
        --match_exact_process_name \
        --kill_process \
        --computergroup Testing \
        "$verbosity" \
        "$url" \
        --replace

# elif [[ $test_type == "package" || $test_type == "pkg" ]]; then
#     # upload a package
#     "$DIR"/../jamf-upload.sh pkg \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --pkg "/Users/gpugh/Library/AutoPkg/Cache/com.github.mlbz521.pkg.Solstice/Solstice-5.4.30427.pkg" \
#         --pkg-name "Solstice-5.4.30427.pkg" \
#         --nsme "Solstice-5.4.30427" \
#         --category Applications \
#         --info "Uploaded directly by JamfPackageUploader in JCDS mode" \
#         --notes "$(date)" \
#         "$verbosity" \
#         "$url" \
#         --jcds \
#         --replace

elif [[ $test_type == "package" || $test_type == "pkg" ]]; then
    # upload a package
    "$DIR"/../jamf-upload.sh pkg \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --pkg-path "/Users/gpugh/sourcecode/erase-install/pkg/erase-install/build/erase-install-29.2.pkg" \
        --pkg-name "erase-install-29.2.pkg" \
        --name "erase-install-29.2" \
        --category "Testing" \
        "$verbosity" \
        "$url" \
        --jcds \
        --replace

elif [[ $test_type == "pkgclean" ]]; then
    # cleanup a package type
    "$DIR"/../jamf-upload.sh pkgclean \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "erase-install" \
        --keep "3" \
        "$verbosity" \
        "$url"

elif [[ $test_type == "script" ]]; then
    # upload a script
    "$DIR"/../jamf-upload.sh script \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft Office License Type.sh" \
        --script "Microsoft Office License Type.sh" \
        --script_parameter4 "License Type" \
        "$verbosity" \
        "$url" \
        --replace

# elif [[ $test_type == "patch" ]]; then
#     # upload a policy
#     "$DIR"/../jamf-upload.sh patch \
#         --prefs "$prefs" \
#         --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
#         --name "Google Chrome" \
#         --title "Google Chrome" \
#         --policy-name "Install Latest Google Chrome" \
#         --template "templates/PatchTemplate-selfservice.xml" \
#         --pkg-name "Google Chrome-91.0.4472.77.pkg" \
#         --version "91.0.4472.77" \
#         "$verbosity" \
#         "$url" \
#         --replace

elif [[ $test_type == "patch" ]]; then
    # upload a policy
    "$DIR"/../jamf-upload.sh patch \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Firefox" \
        --title "Firefox" \
        --template "templates/PatchTemplate-selfservice.xml" \
        --pkg-name "Firefox-96.0.pkg" \
        --version "96.0" \
        --policy-name "Install Latest Firefox" \
        --key PATCH_ENABLED="true" \
        "$verbosity" \
        "$url" \
        --replace


elif [[ $test_type == "dock" ]]; then
    # upload a dock item
    "$DIR"/../jamf-upload.sh dock \
        --prefs "$prefs" \
        --name "ETH Self Service" \
        --type "App" \
        --path "/Applications/ETH Self Service.app/" \
        "$verbosity" \
        "$url" \
        --replace

# elif [[ $test_type == "icon" ]]; then
#     # upload an icon
#     "$DIR"/../jamf-upload.sh icon \
#         --prefs "$prefs" \
#         --icon-uri "https://ics.services.jamfcloud.com/icon/hash_13139b4d9732a8b2fa3bbe25e6c6373e8ef6b85a7c7ba2bd15615195d63bc648" \
#         "$verbosity" \
#         "$url"

elif [[ $test_type == "icon" ]]; then
    # upload an icon
    "$DIR"/../jamf-upload.sh icon \
        --prefs "$prefs" \
        --icon "/tmp/Apple Configurator.png" \
        "$verbosity" \
        "$url"

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
        "$url" \
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
        --patch-uploaded \
        --patch_name "Test Patch Policy" \
        "$verbosity" \
        "$url" \
        --replace

else
    echo "Usage: test.sh [test_type]"
fi

# revert url
if [[ $usual_url ]]; then
    defaults write "$prefs" JSS_URL "$usual_url"
fi