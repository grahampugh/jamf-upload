#!/bin/bash

# JamfUploader tests

# this folder
DIR=$(dirname "$0")

# which test?
test_type="$1"
verbosity="$2"
url="$3"

# path to test items
# pkg_path="/Users/Shared/plistyamlplist-0.6.4.pkg"
pkg_path="/Users/gpugh/Downloads/vanta-universal.pkg"
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

if [[ ! $verbosity ]]; then
    verbosity="-v"
fi

if [[ $url ]]; then
    usual_url=$(defaults read "$prefs" JSS_URL)
    defaults write "$prefs" JSS_URL "$url"
fi

if [[ $test_type == "ldap_server" ]]; then
    # upload an ldap server
    "$DIR"/../jamf-upload.sh ldap_server \
        --prefs "$prefs" \
        --name "d.ethz.ch" \
        --template "/Users/gpugh/sourcecode/id-mac-tools/jamf-api-tools/templates/LDAPServerETH.xml" \
        "$verbosity" \
        --replace

# example object types (Classic API)
# computer_group
# os_x_configuration_profile
# configuration_profile
# mac_application
# mobile_device_application

# example object types (Jamf Pro API)
# script

elif [[ $test_type == "obj-category" ]]; then
    # upload a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh obj \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "category" \
        --name "Testing" \
        --template "templates/Category-Template-Testing.json" \
        "$verbosity" \
        --replace

elif [[ $test_type == "obj-profile" ]]; then
    # upload a generic Classic API object
    "$DIR"/../jamf-upload.sh obj \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "os_x_configuration_profile" \
        --name "VLC Settings" \
        --template "templates/Profile-VLC-settings.xml" \
        "$verbosity" \
        --replace


elif [[ $test_type == "read-distributionpoint" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "distribution_point" \
        --name "test-dp" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-policy" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "policy" \
        --name "Firefox" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-mobiledeviceapp" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs_alt" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "mobile_device_application" \
        --name "Jamf Self Service" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-macapp" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "mac_application" \
        --name "Numbers" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-profile" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "os_x_configuration_profile" \
        --name "Nudge" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-profiles" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "os_x_configuration_profile" \
        --all \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-ea" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "computer_extension_attribute" \
        --name "AdobeFlashVersion" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-eas" ]]; then
    # read a generic Classic API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "computer_extension_attribute" \
        --all \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-script" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "script" \
        --name "SpotifyPostinstall.sh" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-category" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "category" \
        --name "Applications" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-categories" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "category" \
        --all \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-prestage" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs_alt" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "computer_prestage" \
        --name "1:1" \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-prestages" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs_alt" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "computer_prestage" \
        --all \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "read-device-prestages" ]]; then
    # read a generic Jamf Pro API object
    "$DIR"/../jamf-upload.sh read \
        --prefs "$prefs_alt" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "mobile_device_prestage" \
        --all \
        --output "/Users/Shared/Jamf/JamfUploaderTests" \
        "$verbosity"

elif [[ $test_type == "category" ]]; then
    # upload a category
    "$DIR"/../jamf-upload.sh category \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name JamfUploadTest \
        --priority 18 \
        "$verbosity" \
        --replace

elif [[ $test_type == "group" ]]; then
    # upload a computer group
    "$DIR"/../jamf-upload.sh group \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Firefox & stuff test users" \
        --template "templates/SmartGroupTemplate-test-users.xml" \
        --key POLICY_NAME="Firefox & stuff" \
        "$verbosity" \
        --replace

elif [[ $test_type == "delete-group" ]]; then
    # delete a computer group
    "$DIR"/../jamf-upload.sh delete \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "computer_group" \
        --name "1Password-update-smart" \
        "$verbosity"

elif [[ $test_type == "delete-script" ]]; then
    # delete a computer group
    "$DIR"/../jamf-upload.sh delete \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --type "script" \
        --name "EndNote-postinstall.sh" \
        "$verbosity"

elif [[ $test_type == "mobiledevicegroup" ]]; then
    # upload a computer group
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

elif [[ $test_type == "payload" ]]; then
    # upload a profile (payload plist)
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

elif [[ $test_type == "profile" ]]; then
    # upload a profile (mobileconfig)
    "$DIR"/../jamf-upload.sh profile \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template "templates/ProfileTemplate-test-users.xml" \
        --category JamfUploadTest \
        --computergroup "Testing" \
        --mobileconfig "templates/TestProfileIdentifiers.mobileconfig" \
        "$verbosity" \
        --replace

elif [[ $test_type == "profile2" ]]; then
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
        --replace

elif [[ $test_type == "profile_retain_scope" ]]; then
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
        --replace \
        --retain-existing-scope

elif [[ $test_type == "ea" ]]; then
    # upload an extension attribute
    "$DIR"/../jamf-upload.sh ea \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft AutoUpdate Version" \
        --script "templates/MicrosoftAutoUpdate-EA.sh" \
        "$verbosity" \
        --replace

elif [[ $test_type == "macapp" ]]; then
    # upload a mac app
    "$DIR"/../jamf-upload.sh macapp \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Bitwarden" \
        --template "templates/MacApp-allcomputers.xml" \
        --key CATEGORY="JSPP - Applications" \
        --key DEPLOYMENT_TYPE="Make Available in Self Service" \
        "$verbosity" \
        --replace

elif [[ $test_type == "macapp2" ]]; then
    # clone a mac app with no scope
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

elif [[ $test_type == "mobiledeviceappauto" ]]; then
    # clone a mac app with no scope
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

elif [[ $test_type == "mobiledeviceappautoconfig" ]]; then
    # clone a mac app with no scope
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

elif [[ $test_type == "mobiledeviceappselfservice" ]]; then
    # clone a mac app with no scope
    "$DIR"/../jamf-upload.sh mobiledeviceapp \
        --prefs "$prefs" \
        --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
        --name "Keynote" \
        --template "templates/MobileDeviceApp-noscope.xml" \
        --key CATEGORY="Applications" \
        --key DEPLOYMENT_TYPE="Make Available in Self Service" \
        "$verbosity" \
        --replace

elif [[ $test_type == "mobiledeviceappselfserviceconfig" ]]; then
    # clone a mac app with no scope
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

elif [[ $test_type == "mobiledeviceapp-fromread" ]]; then
    # clone a mac app with no scope
    "$DIR"/../jamf-upload.sh mobiledeviceapp \
        --prefs "$prefs_alt" \
        --recipe-dir /Users/Shared/GitHub/jamf-upload/_tests \
        --name "Jamf Self Service" \
        --template "/Users/Shared/Jamf/JamfUploaderTests/MobileDeviceApp-Template-JamfSelfService.xml" \
        "$verbosity" \
        --replace

elif [[ $test_type == "mobiledeviceprofile" ]]; then
    # upload a mobile device profile (mobileconfig)
    "$DIR"/../jamf-upload.sh mobiledeviceprofile \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --template "templates/MobileDeviceProfileTemplate-test-users.xml" \
        --category JamfUploadTest \
        --mobiledevicegroup "Testing" \
        --mobileconfig "templates/AllowScreenRecording.mobileconfig" \
        "$verbosity" \
        --replace

elif [[ $test_type == "policy" ]]; then
    # upload a policy
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

elif [[ $test_type == "policy_retain_scope" ]]; then
    # upload a policy (retain scope)
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

elif [[ $test_type == "policydelete" ]]; then
    # delete a policy
    "$DIR"/../jamf-upload.sh policydelete \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Install Latest Adium" \
        "$verbosity"

elif [[ $test_type == "policy_flush" ]]; then
    # flush a policy
    "$DIR"/../jamf-upload.sh policy_flush \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "0001 - Install Rosetta 2" \
        --interval "Zero Days" \
        "$verbosity"

elif [[ $test_type == "account" ]]; then
    # upload a group
    "$DIR"/../jamf-upload.sh account \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Test Group" \
        --type "group" \
        --template "templates/Account-Group-local.xml" \
        "$verbosity"

elif [[ $test_type == "account2" ]]; then
    # upload an account with group access
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

elif [[ $test_type == "account3" ]]; then
    # upload an account with full access
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
        --replace

elif [[ $test_type == "pkg" ]]; then
    # upload a package
    "$DIR"/../jamf-upload.sh pkg \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --pkg "$pkg_path" \
        --pkg-name "$(basename "$pkg_path")" \
        --name "$(basename "$pkg_path")" \
        --category JamfUploadTest \
        --info "Uploaded directly by JamfPackageUploader using v1/packages" \
        --notes "$(date)" \
        "$verbosity" \
        --replace
    # --md5 \
    # --recalculate \

elif [[ $test_type == "pkg-noreplace" ]]; then
    # upload a package but don't replace an existing one
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
    # --recalculate \

elif [[ $test_type == "pkg-jcds2" ]]; then
    /usr/local/autopkg/python -m pip install boto3

    # upload a package (JCDS2 mode)
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
    # --name "erase-install-30" \

elif [[ $test_type == "pkg-aws" ]]; then
    /usr/local/autopkg/python -m pip install boto3

    # upload a package (AWS-CLI mode)
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
    # --name "erase-install-30" \

elif [[ $test_type == "pkgclean" ]]; then
    # cleanup a package type
    "$DIR"/../jamf-upload.sh pkgclean \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --keep "3" \
        --key "NAME=plistyamlplist" \
        "$verbosity"
    # --name "erase-install" \

elif [[ $test_type == "pkgcalc" ]]; then
    # recalculate a package
    "$DIR"/../jamf-upload.sh pkgcalc \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        "$verbosity"

elif [[ $test_type == "script" ]]; then
    # upload a script
    "$DIR"/../jamf-upload.sh script \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "Microsoft Office License Type.sh" \
        --script "templates/Microsoft Office License Type.sh" \
        --script_parameter4 "License Type" \
        "$verbosity" \
        --replace

elif [[ $test_type == "patch" ]]; then
    # upload a patch policy
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

elif [[ $test_type == "patch2" ]]; then
    # upload a patch policy
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

elif [[ $test_type == "icon" ]]; then
    # upload an icon from a URL
    "$DIR"/../jamf-upload.sh icon \
        --prefs "$prefs" \
        --icon-uri "https://ics.services.jamfcloud.com/icon/hash_13139b4d9732a8b2fa3bbe25e6c6373e8ef6b85a7c7ba2bd15615195d63bc648" \
        "$verbosity" \
        "$url"

elif [[ $test_type == "icon2" ]]; then
    # upload an icon from a file
    "$DIR"/../jamf-upload.sh icon \
        --prefs "$prefs" \
        --icon "/tmp/Apple Configurator.png" \
        "$verbosity" \
        "$url"

elif [[ $test_type == "apirole" ]]; then
    # upload an API role
    "$DIR"/../jamf-upload.sh apirole \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "JamfUploader Test API Role" \
        --template "templates/APIRoleTemplate-example.json" \
        "$verbosity" \
        --replace

elif [[ $test_type == "apiclient" ]]; then
    # upload an API client
    "$DIR"/../jamf-upload.sh apiclient \
        --prefs "$prefs" \
        --recipe-dir /Users/gpugh/sourcecode/jamf-upload/_tests \
        --name "JamfUploader Test API Client" \
        --api-role-name "JamfUploader Test API Role" \
        --lifetime "150" \
        --enabled \
        "$verbosity" \
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
        "$url" \
        --replace

elif [[ $test_type == "teams" ]]; then
    # send a webhook to teams
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
