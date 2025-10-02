#!/bin/bash

# JamfUploader tests

# this folder
DIR=$(dirname "$0")

# which test?
test_type="$1"
verbosity="$2"
url="$3"
jira_project="$4"
jira_user="$5"
jira_api_token="$6"

# path to test items
pkg_path="/Users/gpugh/Downloads/Workbrew-1.1.7.pkg"
pkg_name="$(basename "$pkg_path")"

# other variables (ensure some of the temporary variables are not in the prefs)
# These keys are required to interact with a Jamf instance
# JSS_URL
# API_USERNAME
# API_PASSWORD
prefs="$HOME/Library/Preferences/com.github.autopkg.plist"
prefs_alt="/Users/Shared/com.github.autopkg.plist"

# ensure pkg upload modes are disabled
defaults write "$prefs" jcds_mode -bool False
defaults write "$prefs" jcds2_mode -bool False
defaults write "$prefs" aws_cdp_mode -bool False
defaults write "$prefs" pkg_api_mode -bool False

# slack webhook url
slack_webhook_url=$(cat /Users/gpugh/sourcecode/multitenant-jamf-tools/slack-webhooks/tst.txt)

if [[ ! $verbosity ]]; then
    verbosity="-v"
fi

if [[ $url ]]; then
    usual_url=$(defaults read "$prefs" JSS_URL)
    defaults write "$prefs" JSS_URL "$url"
fi

# example object types (Classic API)
# computer_group
# os_x_configuration_profile
# configuration_profile
# mac_application
# mobile_device_application

# example object types (Jamf Pro API)
# script

case "$test_type" in
    list-policies)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "policy" \
            --list \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    list-policies-user)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "policy" \
            --list \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            --key CLIENT_ID=c611d89d-471b-40d2-855d-08647131fc1d \
            "$verbosity"
        ;;
    list-scripts)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "script" \
            --list \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    list-groups)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_group" \
            --list \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    scope)
        echo "Running scope test"
        "$DIR"/../jamf-upload.sh scope \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-policies-Firefox.xml" \
            --scope-type "target" \
            --operation "remove" \
            --type "computer_group" \
            --name "Testing" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            --not-strict \
            "$verbosity"
        ;;
    ea-popup-remove)
        echo "Running EA popup remove test"
        "$DIR"/../jamf-upload.sh eapopup \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-computer_extension_attributes-Test Popup.json" \
            --operation "remove" \
            --value "1.3" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            --not-strict \
            "$verbosity"
        ;;
    ea-popup-add)
        echo "Running EA popup add test"
        "$DIR"/../jamf-upload.sh eapopup \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-computer_extension_attributes-Test Popup.json" \
            --operation "add" \
            --value "1.3" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            --not-strict \
            "$verbosity"
        ;;
    ldapserver)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs" \
            --type "ldapserver" \
            --name "d.ethz.ch" \
            --template "/Users/gpugh/sourcecode/id-mac-tools/jamf-api-tools/templates/LDAPServerETH.xml" \
            "$verbosity" \
            --replace
        ;;
    enrollment)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "enrollment_settings" \
            --template "templates/enrollment.json" \
            "$verbosity"
        ;;
    inventory)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_inventory_collection_settings" \
            --template "templates/computer-inventory-collection-settings.json" \
            "$verbosity"
        ;;
    laps)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "laps_settings" \
            --template "templates/local-admin-password-settings.json" \
            "$verbosity"
        ;;
    selfservice)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "self_service_settings" \
            --template "templates/self-service-settings.json" \
            "$verbosity"
        ;;
    obj-category)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "category" \
            --name "Testing" \
            --template "templates/Category-Template-Testing.json" \
            "$verbosity" \
            --replace
        ;;
    obj-profile)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "os_x_configuration_profile" \
            --name "VLC Settings" \
            --template "templates/Profile-VLC-settings.xml" \
            "$verbosity" \
            --replace
        ;;
    obj-policy-id)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "policy" \
            --id "15" \
            --name "Firefox - Ongoing" \
            --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-policies-Firefox.xml" \
            "$verbosity" \
            --replace
        ;;
    obj-script-id)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "script" \
            --id "22" \
            --name "Spotify-postinstall.sh" \
            --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-scripts-SpotifyPostinstall.sh.json" \
            "$verbosity" \
            --replace
        ;;
    read-distributionpoint)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "distribution_point" \
            --name "test-dp" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    appinstallers-tandc)
        "$DIR"/../jamf-upload.sh obj \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "app_installers_accept_t_and_c_command" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-appinstaller-id)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "app_installer" \
            --id "1" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-policy)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "policy" \
            --name "Firefox" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-mobiledeviceapp)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "mobile_device_application" \
            --name "Jamf Self Service" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-macapp)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "mac_application" \
            --name "Numbers" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-profile)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "os_x_configuration_profile" \
            --name "Nudge" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-profiles)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "os_x_configuration_profile" \
            --all \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-ea)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_extension_attribute" \
            --name "AdobeFlashVersion" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-ea-popup)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_extension_attribute" \
            --name "Test Popup" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-eas)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_extension_attribute" \
            --all \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-script)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "script" \
            --name "SpotifyPostinstall.sh" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-script-id)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "script" \
            --id "22" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-category)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "category" \
            --name "Applications" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-categories)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "category" \
            --all \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-prestage)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_prestage" \
            --name "Test PreStage" \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-prestages)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_prestage" \
            --all \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    read-device-prestages)
        "$DIR"/../jamf-upload.sh read \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "mobile_device_prestage" \
            --all \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            "$verbosity"
        ;;
    category)
        "$DIR"/../jamf-upload.sh category \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name JamfUploadTest \
            --priority 18 \
            "$verbosity" \
            --replace
        ;;
    group)
        "$DIR"/../jamf-upload.sh group \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Firefox & stuff test users" \
            --template "templates/SmartGroupTemplate-test-users.xml" \
            --key POLICY_NAME="Firefox & stuff" \
            "$verbosity" \
            --replace
        ;;
    delete-group)
        "$DIR"/../jamf-upload.sh delete \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "computer_group" \
            --name "1Password-update-smart" \
            "$verbosity"
        ;;
    delete-script)
        "$DIR"/../jamf-upload.sh delete \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --type "script" \
            --name "EndNote-postinstall.sh" \
            "$verbosity"
        ;;
    mobiledevicegroup)
        "$DIR"/../jamf-upload.sh mobiledevicegroup \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Allow Screen Recording" \
            --template "templates/AllowScreenRecording-mobiledevicegroup.xml" \
            --key GROUP_NAME="Allow Screen Recording" \
            --key TESTING_GROUP_NAME="Testing" \
            --key custom_curl_opts="--max-time 3600" \
            "$verbosity" \
            --replace
        ;;
    msu)
        "$DIR"/../jamf-upload.sh msu \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --device-type "computer" \
            --group "Testing" \
            --version "latest-minor" \
            --days "14" \
            "$verbosity"
        ;;
    payload)
        "$DIR"/../jamf-upload.sh profile \
            --prefs "$prefs" \
            --name "Carbon Copy Cloner" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "templates/ProfileTemplate-1-group-1-exclusion.xml" \
            --payload "templates/com.bombich.ccc.plist" \
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
            --key EXCLUSION_GROUP_NAME="Firefox test users" \
            --replace
        ;;
    profile)
        "$DIR"/../jamf-upload.sh profile \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "templates/ProfileTemplate-test-users.xml" \
            --category JamfUploadTest \
            --computergroup "Testing" \
            --mobileconfig "templates/TestProfileIdentifiers.mobileconfig" \
            "$verbosity" \
            --replace
        ;;
    profile2)
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
            --replace
        ;;
    profile_retain_scope)
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
            --replace \
            --retain-existing-scope
        ;;
    ea)
        "$DIR"/../jamf-upload.sh ea \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Microsoft AutoUpdate Version" \
            --script "templates/MicrosoftAutoUpdate-EA.sh" \
            "$verbosity" \
            --replace
        ;;
    ea-popup)
        "$DIR"/../jamf-upload.sh ea \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Test Popup" \
            --type "popup" \
            --choices "1.0,1.1,1.2,1.3" \
            --description "Choose a version" \
            --inventory-display "General" \
            "$verbosity" \
            --replace
        ;;
    mea-popup)
        "$DIR"/../jamf-upload.sh mobiledeviceea \
            --prefs "$prefs" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Test Popup" \
            --type "popup" \
            --choices "1.0,1.1,1.2,1.3" \
            --description "Choose a version" \
            --inventory-display "General" \
            "$verbosity" \
            --replace
        ;;
    macapp)
        "$DIR"/../jamf-upload.sh macapp \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Bitwarden" \
            --template "templates/MacApp-allcomputers.xml" \
            --key CATEGORY="JSPP - Applications" \
            --key DEPLOYMENT_TYPE="Make Available in Self Service" \
            "$verbosity" \
            --replace
        ;;
    macapp2)
        "$DIR"/../jamf-upload.sh macapp \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Bitwarden - auto-install" \
            --clone-from "Bitwarden" \
            --template "templates/MacApp-noscope-autoinstall.xml" \
            --key CATEGORY="JSPP - Applications" \
            --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceappauto)
        "$DIR"/../jamf-upload.sh mobiledeviceapp \
            --prefs "$prefs" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Keynote - Automatic" \
            --clone-from "Keynote" \
            --template "templates/MobileDeviceApp-noscope-autoinstall.xml" \
            --key CATEGORY="Applications" \
            --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceappautoconfig)
        "$DIR"/../jamf-upload.sh mobiledeviceapp \
            --prefs "$prefs" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Keynote - Automatic" \
            --clone-from "Keynote" \
            --template "templates/MobileDeviceApp-noscope-autoinstall.xml" \
            --appconfig "templates/AppConfig.xml" \
            --key CATEGORY="Applications" \
            --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceappselfservice)
        "$DIR"/../jamf-upload.sh mobiledeviceapp \
            --prefs "$prefs" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Keynote" \
            --template "templates/MobileDeviceApp-noscope.xml" \
            --key CATEGORY="Applications" \
            --key DEPLOYMENT_TYPE="Make Available in Self Service" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceappselfserviceconfig)
        "$DIR"/../jamf-upload.sh mobiledeviceapp \
            --prefs "$prefs" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Keynote" \
            --template "templates/MobileDeviceApp-noscope.xml" \
            --appconfig "templates/AppConfig.xml" \
            --key CATEGORY="Applications" \
            --key DEPLOYMENT_TYPE="Make Available in Self Service" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceapp-fromread)
        "$DIR"/../jamf-upload.sh mobiledeviceapp \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
            --name "Jamf Self Service" \
            --template "/Users/Shared/Jamf/JamfUploaderTests/MobileDeviceApp-Template-JamfSelfService.xml" \
            "$verbosity" \
            --replace
        ;;
    mobiledeviceprofile)
        "$DIR"/../jamf-upload.sh mobiledeviceprofile \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --template "templates/MobileDeviceProfileTemplate-test-users.xml" \
            --category JamfUploadTest \
            --mobiledevicegroup "Testing" \
            --mobileconfig "templates/AllowScreenRecording.mobileconfig" \
            "$verbosity" \
            --replace
        ;;
    policy)
        "$DIR"/../jamf-upload.sh policy \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Install plistyamlplist" \
            --template "templates/PolicyTemplate-trigger.xml" \
            --key POLICY_NAME="Install plistyamlplist" \
            --key TRIGGER_NAME="plistyamlplist-install" \
            --key CATEGORY="JamfUploadTest" \
            --key pkg_name="$pkg_name" \
            "$verbosity" \
            --replace
        ;;
    policy_retain_scope)
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
            --replace \
            --retain-existing-scope
        ;;
    prestage)
        "$DIR"/../jamf-upload.sh computerprestage \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Test PreStage 3" \
            --template "templates/computer-prestage-example.json" \
            "$verbosity" \
            --replace
        ;;
    prestage2)
        "$DIR"/../jamf-upload.sh computerprestage \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Test PreStage with Account" \
            --template "templates/computer-prestage-example-account.json" \
            "$verbosity" \
            --replace
        ;;
    account)
        "$DIR"/../jamf-upload.sh account \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Test Group" \
            --type "group" \
            --template "templates/Account-Group-local.xml" \
            "$verbosity"
        ;;
    account2)
        "$DIR"/../jamf-upload.sh account \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "graham" \
            --type "user" \
            --template "templates/Account-User-groupaccess.xml" \
            --key ACCOUNT_FULLNAME="Graham Pugh Test Account" \
            --key ACCOUNT_PASSWORD="GrahamsPassword" \
            --key ACCOUNT_EMAIL="graham@pugh.com" \
            --key GROUP_NAME="Test Group" \
            "$verbosity"
        ;;
    account3)
        "$DIR"/../jamf-upload.sh account \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "graham" \
            --type "user" \
            --template "templates/Account-User-fullaccess.xml" \
            --key ACCOUNT_FULLNAME="Graham Pugh Test Account" \
            --key ACCOUNT_EMAIL="graham@pugh.com" \
            "$verbosity" \
            --replace
        ;;
    restriction)
        "$DIR"/../jamf-upload.sh restriction \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Restrict Carbon Copy Cloner" \
            --template "templates/RestrictionTemplate-singlegroup.xml" \
            --process_name "Carbon Copy Cloner" \
            --display_message "Carbon Copy Cloner is not allowed." \
            --match_exact_process_name \
            --kill_process \
            --computergroup Testing \
            "$verbosity" \
            --replace
        ;;
    script)
        "$DIR"/../jamf-upload.sh script \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Microsoft Office License Type.sh" \
            --script "templates/Microsoft Office License Type.sh" \
            --script_parameter4 "License Type" \
            "$verbosity" \
            --replace
        ;;
    patch)
        "$DIR"/../jamf-upload.sh patch \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Installomator" \
            --title "Installomator" \
            --policy-name "Install Latest Installomator" \
            --template "templates/PatchTemplate-selfservice.xml" \
            --pkg-name "Installomator-10.5.pkg" \
            --version "10.5" \
            "$verbosity" \
            "$url" \
            --replace
        ;;
    patch2)
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
            --replace
        ;;
    dock)
        "$DIR"/../jamf-upload.sh dock \
            --prefs "$prefs" \
            --name "ETH Self Service" \
            --type "App" \
            --path "/Applications/ETH Self Service.app/" \
            "$verbosity" \
            --replace
        ;;
    icon)
        "$DIR"/../jamf-upload.sh icon \
            --prefs "$prefs" \
            --icon-uri "https://ics.services.jamfcloud.com/icon/hash_13139b4d9732a8b2fa3bbe25e6c6373e8ef6b85a7c7ba2bd15615195d63bc648" \
            "$verbosity"
        ;;
    icon2)
        "$DIR"/../jamf-upload.sh icon \
            --prefs "$prefs" \
            --icon "/tmp/Apple Configurator.png" \
            "$verbosity"
        ;;
    apirole)
        "$DIR"/../jamf-upload.sh apirole \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "JamfUploader Test API Role" \
            --template "templates/APIRoleTemplate-example.json" \
            "$verbosity" \
            --replace
        ;;
    apiclient)
        "$DIR"/../jamf-upload.sh apiclient \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "JamfUploader Test API Client" \
            --api-role-name "JamfUploader Test API Role" \
            --lifetime "150" \
            --enabled \
            "$verbosity" \
            --replace
        ;;
    policydelete)
        "$DIR"/../jamf-upload.sh policydelete \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "Install Latest Adium" \
            "$verbosity"
        ;;
    policy_flush)
        "$DIR"/../jamf-upload.sh policy_flush \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --name "0001 - Install Rosetta 2" \
            --interval "Zero Days" \
            "$verbosity"
        ;;
    pkg)
        "$DIR"/../jamf-upload.sh pkg \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --pkg "$pkg_path" \
            --pkg-name "$(basename "$pkg_path")" \
            --name "$(basename "$pkg_path")" \
            --category JamfUploadTest \
            --info "Uploaded directly by JamfPackageUploader using v1/packages" \
            --notes "$(date)" \
            "$verbosity" \
            --replace
        ;;
    pkg-noreplace)
        "$DIR"/../jamf-upload.sh pkg \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --pkg "$pkg_path" \
            --pkg-name "$(basename "$pkg_path")" \
            --name "$(basename "$pkg_path")" \
            --category JamfUploadTest \
            --info "Uploaded directly by JamfPackageUploader using v1/packages" \
            --notes "$(date)" \
            "$verbosity"
        ;;
    pkg-jcds2)
        "$DIR"/../jamf-upload.sh pkg \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --pkg "$pkg_path" \
            --pkg-name "$(basename "$pkg_path")" \
            --name "$(basename "$pkg_path")" \
            --category "Testing" \
            --info "Uploaded directly by JamfPackageUploader in JCDS mode" \
            "$verbosity" \
            --jcds2 \
            --replace
        ;;
    pkg-aws)
        "$DIR"/../jamf-upload.sh pkg \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --pkg "$pkg_path" \
            --pkg-name "$(basename "$pkg_path")" \
            --name "$(basename "$pkg_path")" \
            --category "Testing" \
            "$verbosity" \
            --info "Uploaded directly by JamfPackageUploader in AWS-CLI mode" \
            --aws \
            --key "S3_BUCKET_NAME=jamf2360b29f101f4e0881cf6422ee2be25e" \
            --replace
        ;;
    pkgclean)
        "$DIR"/../jamf-upload.sh pkgclean \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --keep "3" \
            --key "NAME=plistyamlplist" \
            "$verbosity"
        ;;
    unusedpkg)
        "$DIR"/../jamf-upload.sh unusedpkgclean \
            --prefs "$prefs_alt" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --output "/Users/Shared/Jamf/JamfUploaderTests" \
            --slack-url "$slack_webhook_url" \
            "$verbosity"
        ;;
            # --dry-run \
    pkgcalc)
        "$DIR"/../jamf-upload.sh pkgcalc \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            "$verbosity"
        ;;
    pkgdata)
        "$DIR"/../jamf-upload.sh pkgdata \
            --prefs "$prefs" \
            --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
            --pkg-name "$(basename "$pkg_path")" \
            --name "$(basename "$pkg_path")" \
            --category JamfUploadTest \
            --info "Updated by JamfPkgMetadataUploader" \
            --notes "$(date)" \
            "$verbosity" \
            --replace
        ;;
    jira)
        "$DIR"/../jamf-upload.sh jira \
            --prefs "$prefs" \
            --name "JamfUploaderJiraIssueCreator Test - please ignore" \
            --policy-name "JamfUploaderJiraIssueCreator Test" \
            --policy-category "Applications" \
            --pkg-category "Packages" \
            --pkg-name "Test-Package.pkg" \
            --patch-name "Test Patch Policy" \
            --version "1.2.3" \
            --patch-uploaded \
            --pkg-uploaded \
            --policy-uploaded \
            --jira-user "$jira_user" \
            --jira-project "$jira_project" \
            --jira-priority "5" \
            --jira-issue "10001" \
            --jira-api-token "$jira_api_token" \
            --jira-url "$url/rest/api/3/issue/" \
            "$verbosity"
        ;;
    slack)
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
            "$verbosity"
        ;;
    teams)
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
            --patch-name "Test Patch Policy" \
            "$verbosity"
        ;;
    *)
        echo "Unknown test type: $test_type"
        echo "Usage: test.sh [test_type]"
        ;;
esac

# revert url
if [[ $usual_url ]]; then
    defaults write "$prefs" JSS_URL "$usual_url"
fi
