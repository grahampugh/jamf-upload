#!/bin/bash

# JamfUploader tests

# this folder
DIR=$(dirname "$0")

# Command line override for the above settings
while [[ "$#" -gt 0 ]]; do
    key="$1"
    case $key in
    -t | --test)
        shift
        test_type="$1"
    ;;
    -u | --url)
        shift
        url="$1"
    ;;
    -r | --region)
        shift
        region="$1"
    ;;
    --tenant)
        shift
        tenant_id="$1"
    ;;
    --profile)
        shift
        profile="$1"
    ;;
    --clientid)
        shift
        client_id="$1"
    ;;
    -p | --pkg)
        shift
        pkg_path="${1}"
    ;;
    -jp | --jira-project)
        shift
        jira_project="$1"
    ;;
    -ju | --jira-user)
        shift
        jira_user="$1"
    ;;
    -jt | --jira-api-token)
        shift
        jira_api_token="$1"
    ;;
    --prefs)
        shift
        prefs="$1"
        prefs_alt="$1"
    ;;
    --slack)
        shift
        slack_webhook_url="$1"
    ;;
    -o | --open)
        open_results=1
    ;;
    -v*)
        verbosity="$1"
    ;;
    -h | --help)
        echo "Usage: test.sh -t|--test TEST_TYPE [-u|--url JAMF_URL] [-v VERBOSITY]"
        echo "Available TEST_TYPE values:"
        echo "  list-types"
        echo "  list-groups"
        echo "  read-group"
        echo "  list-policies"
        echo "  list-policies-user"
        echo "  list-pkgs"
        echo "  list-scripts"
        echo "  list-computer-groups"
        echo "  scope"
        echo "  ea-popup-remove"
        echo "  ea-popup-add"
        echo "  ldapserver"
        echo "  enrollment"
        echo "  inventory"
        echo "  laps"
        echo "  selfservice"
        echo "  obj-category"
        echo "  obj-smartgroup-computer"
        echo "  staticgroup-computer"
        echo "  obj-smartgroup-mobile"
        echo "  staticgroup-mobile"
        echo "  obj-profile"
        echo "  obj-policy-id"
        echo "  obj-script-id"
        echo "  read-distributionpoint"
        echo "  appinstallers-tandc"
        echo "  read-appinstaller-id"
        echo "  read-policy"
        echo "  read-mobiledeviceapp"
        echo "  read-macapp"
        echo "  read-profile"
        echo "  read-profiles"
        echo "  read-ea"
        echo "  read-ea-popup"
        echo "  read-eas"
        echo "  read-script"
        echo "  read-script-id"
        echo "  read-category"
        echo "  read-categories"
        echo "  read-prestage"
        echo "  read-prestages"
        echo "  read-device-prestages"
        echo "  category"
        echo "  group"
        echo "  delete-group"
        echo "  delete-pkg"
        echo "  delete-script"
        echo "  mobiledevicegroup"
        echo "  msu"
        echo "  payload"
        echo "  profile"
        echo "  profile2"
        echo "  profile_retain_scope"
        echo "  ea"
        echo "  ea-popup"
        echo "  mea-popup"
        echo "  macapp"
        echo "  macapp2"
        echo "  mobiledeviceappauto"
        echo "  mobiledeviceappautoconfig"
        echo "  mobiledeviceappselfservice"
        echo "  mobiledeviceappselfserviceconfig"
        echo "  mobiledeviceapp-fromread"
        echo "  mobiledeviceprofile"
        echo "  policy"
        echo "  policy-retain-scope"
        echo "  prestage"
        echo "  prestage2"
        echo "  account"
        echo "  account2"
        echo "  account3"
        echo "  restriction"
        echo "  script"
        echo "  patch"
        echo "  patch2"
        echo "  pkg"
        echo "  pkg-plus-calc"
        echo "  dock"
        echo "  icon"
        echo "  apirole"
        echo "  apiclient"
        echo "  delete-policy"
        echo "  policyflush"
        echo "  pkg-noreplace"
        echo "  pkg-jcds2"
        echo "  pkg-aws"
        echo "  pkgclean"
        echo "  unusedpkg"
        echo "  pkgcalc"
        echo "  pkgdata"
        echo "  statechange"
        echo "  jira"
        echo "  slack"
        echo "  teams"
        echo "  skip"
        exit
    ;;
    *)
        echo "Unknown option: $1"
        exit 1
    ;;
    esac
    # Shift after checking all the cases to get the next option
    shift
done

# path to test items
if [[ ! $pkg_path ]]; then
    pkg_path="/Users/gpugh/Downloads/Workbrew-1.1.7.pkg"
fi

# set pkg name
pkg_name="$(basename "$pkg_path")"

# defaults
# Commented out default region - only use region if explicitly provided
# if [[ ! $region ]]; then
#     region="eu"
# fi

# other variables (ensure some of the temporary variables are not in the prefs)
# These keys are required to interact with a Jamf instance
# JSS_URL
# API_USERNAME
# API_PASSWORD
# path to prefs
if [[ ! $prefs ]]; then
    prefs="$HOME/Library/Preferences/com.github.autopkg.plist"
fi

# ensure pkg upload modes are disabled
defaults write "$prefs" jcds_mode -bool False
defaults write "$prefs" jcds2_mode -bool False
defaults write "$prefs" aws_cdp_mode -bool False
defaults write "$prefs" pkg_api_mode -bool False

# slack webhook url
if [[ ! $slack_webhook_url ]]; then
    slack_webhook_url=$(cat /Users/gpugh/sourcecode/multitenant-jamf-tools/slack-webhooks/tst.txt)
fi

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

# common settings for all test types
command_base=(
    "$DIR"/../jamf-upload.sh
    --prefs "$prefs"
    --output "/Users/Shared/Jamf/JamfUploaderTests"
    "$verbosity"
)

if [[ $profile ]]; then
    command_base+=(
        --jamf-cli-profile "$profile"
    )
fi

if [[ $tenant_id ]]; then
    command_base+=(
        --tenant "$tenant_id"
    )
fi

if [[ $region ]]; then
    command_base+=(
        --region "$region"
    )
fi

if [[ $client_id ]]; then
    command_base+=(
        --clientid "$client_id"
    )
fi

# run the appropriate test based on the test type argument
case "$test_type" in
list-types)
    command=(
        "${command_base[@]}"
        list-types
    )
;;
statechange)
    command=(
        "${command_base[@]}"
        statechange
        --type "policy"
        --name "JSPP - Submit Inventory - Self Service"
        --state "disable"
    )
;;
disable)
    command=(
        "${command_base[@]}"
        statechange
        --type "policy"
        --name "JSPP - Submit Inventory - Self Service"
        --state "disable"
    )
;;
enable)
    command=(
        "${command_base[@]}"
        statechange
        --type "policy"
        --name "JSPP - Submit Inventory - Self Service"
        --state "enable"
    )
;;
disable-app)
    command=(
        "${command_base[@]}"
        statechange
        --type "app_installers_deployment"
        --name "Canva"
        --state "disable"
        --retain-data "false"
    )
;;
enable-app)
    command=(
        "${command_base[@]}"
        statechange
        --type "app_installers_deployment"
        --name "Canva"
        --state "enable"
    )
;;
disable-ea)
    command=(
        "${command_base[@]}"
        statechange
        --type "computer_extension_attribute"
        --name "macOS Version Check"
        --state "disable"
        --retain-data "false"
    )
;;
enable-ea)
    command=(
        "${command_base[@]}"
        statechange
        --type "computer_extension_attribute"
        --name "macOS Version Check"
        --state "enable"
    )
;;
list-groups)
    command=(
        "${command_base[@]}"
        read
        --type "group"
        --list
    )
;;
read-group)
    command=(
        "${command_base[@]}"
        read
        --type "group"
        --name "All Managed"
    )
;;
list-policies)
    command=(
        "${command_base[@]}"
        read
        --type "policy"
        --all
        --list
    )
;;
list-policies-user)
    command=(
        "${command_base[@]}"
        read
        --type "policy"
        --list
        --key CLIENT_ID=c611d89d-471b-40d2-855d-08647131fc1d
    )
;;
list-pkgs)
    command=(
        "${command_base[@]}"
        read
        --type "package"
        --all
        --list
    )
;;
list-scripts)
    command=(
        "${command_base[@]}"
        read
        --type "script"
        --list
        --all
    )
;;
list-computer-groups)
    command=(
        "${command_base[@]}"
        read
        --type "computer_group"
        --list
    )
;;
scope)
    echo "Running scope test"
    command=(
        "${command_base[@]}"
        scope
        --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-policies-Firefox.xml"
        --scope-type "target"
        --operation "remove"
        --type "computer_group"
        --name "Testing"
        --not-strict
    )
;;
ea-popup-remove)
    echo "Running EA popup remove test"
    command=(
        "${command_base[@]}"
        eapopup
        --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-computer_extension_attributes-Test Popup.json"
        --operation "remove"
        --value "1.3"
        --not-strict
    )
;;
ea-popup-add)
    echo "Running EA popup add test"
    command=(
        "${command_base[@]}"
        eapopup
        --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-computer_extension_attributes-Test Popup.json"
        --operation "add"
        --value "1.3"
        --not-strict
    )
;;
ldapserver)
    command=(
        "${command_base[@]}"
        obj
        --type "ldapserver"
        --name "d.ethz.ch"
        --template "/Users/gpugh/sourcecode/id-mac-tools/jamf-api-tools/templates/LDAPServerETH.xml"
        --replace
    )
;;
enrollment)
    command=(
        "${command_base[@]}"
        obj
        --type "enrollment_settings"
        --template "templates/enrollment.json"
    )
;;
inventory)
    command=(
        "${command_base[@]}"
        obj
        --type "computer_inventory_collection_settings"
        --template "templates/computer-inventory-collection-settings.json"
    )
;;
laps)
    command=(
        "${command_base[@]}"
        obj
        --type "laps_settings"
        --template "templates/local-admin-password-settings.json"
    )
;;
selfservice)
    command=(
        "${command_base[@]}"
        obj
        --type "self_service_settings"
        --template "templates/self-service-settings.json"
    )
;;
obj-category)
    command=(
        "${command_base[@]}"
        obj
        --type "category"
        --name "Testing"
        --template "templates/Category-Template-Testing.json"
        --replace
    )
;;
obj-smartgroup-computer)
    command=(
        "${command_base[@]}"
        obj
        --type "smart_computer_group"
        --name "Firefox-update-smart"
        --template "templates/SmartGroupTemplate-example-update-smart.json"
        --key GROUP_NAME="Firefox-update-smart"
        --key JSS_INVENTORY_NAME="Firefox.app"
        --key VERSION_CRITERION="Application Version"
        --key version="99.99"
        --key TESTING_STATIC_GROUP="Testing"
        --key GROUP_DESCRIPTION="Created using test.sh"
        --replace
    )
;;
staticgroup-computer)
    command=(
        "${command_base[@]}"
        staticcomputergroup
        --name "Testing - $(date)"
        --description "Generated by Test Script $(date)"
        --replace
    )
;;
staticgroup-mobile)
    command=(
        "${command_base[@]}"
        staticmobiledevicegroup
        --name "Testing - $(date)"
        --description "Generated by Test Script $(date)"
        --clear
        --replace
    )
;;
obj-smartgroup-mobile)
    command=(
        "${command_base[@]}"
        obj
        --type "smart_mobile_device_group"
        --name "Safari Is Installed"
        --template "templates/SmartMobileDeviceGroupTemplate-example.json"
        --key GROUP_NAME="Safari Is Installed"
        --key TESTING_STATIC_GROUP="Testing"
        --key GROUP_DESCRIPTION="Created using test.sh"
        --replace
    )
;;
obj-profile)
    command=(
        "${command_base[@]}"
        obj
        --type "os_x_configuration_profile"
        --name "VLC Settings"
        --template "templates/Profile-VLC-settings.xml"
        --replace
    )
;;
obj-policy-id)
    command=(
        "${command_base[@]}"
        obj
        --type "policy"
        --id "15"
        --name "Firefox - Ongoing"
        --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-policies-Firefox.xml"
        --replace
    )
;;
obj-script-id)
    command=(
        "${command_base[@]}"
        obj
        --type "script"
        --id "22"
        --name "Spotify-postinstall.sh"
        --template "/Users/Shared/Jamf/JamfUploaderTests/jssimporter-scripts-SpotifyPostinstall.sh.json"
        --replace
    )
;;
read-distributionpoint)
    command=(
        "${command_base[@]}"
        read
        --type "distribution_point"
        --name "test-dp"
    )
;;
appinstallers-tandc)
    command=(
        "${command_base[@]}"
        obj
        --type "app_installers_accept_t_and_c_command"
    )
;;
read-appinstaller-id)
    command=(
        "${command_base[@]}"
        read
        --type "app_installer"
        --id "1"
    )
;;
read-policy)
    command=(
        "${command_base[@]}"
        read
        --type "policy"
        --name "Firefox"
    )
;;
read-mobiledeviceapp)
    command=(
        "${command_base[@]}"
        read
        --type "mobile_device_application"
        --name "Jamf Self Service"
    )
;;
read-macapp)
    command=(
        "${command_base[@]}"
        read
        --type "mac_application"
        --name "Numbers"
    )
;;
read-profile)
    command=(
        "${command_base[@]}"
        read
        --type "os_x_configuration_profile"
        --name "Nudge"
    )
;;
read-profiles)
    command=(
        "${command_base[@]}"
        read
        --type "os_x_configuration_profile"
        --all
    )
;;
read-ea)
    command=(
        "${command_base[@]}"
        read
        --type "computer_extension_attribute"
        --name "AdobeFlashVersion"
    )
;;
read-ea-popup)
    command=(
        "${command_base[@]}"
        read
        --type "computer_extension_attribute"
        --name "Test Popup"
    )
;;
read-eas)
    command=(
        "${command_base[@]}"
        read
        --type "computer_extension_attribute"
        --all
    )
;;
read-script)
    command=(
        "${command_base[@]}"
        read
        --type "script"
        --name "SpotifyPostinstall.sh"
    )
;;
read-script-id)
    command=(
        "${command_base[@]}"
        read
        --type "script"
        --id "22"
    )
;;
read-category)
    command=(
        "${command_base[@]}"
        read
        --type "category"
        --name "Applications"
    )
;;
read-categories)
    command=(
        "${command_base[@]}"
        read
        --type "category"
        --all
    )
;;
read-prestage)
    command=(
        "${command_base[@]}"
        read
        --type "computer_prestage"
        --name "Test PreStage"
    )
;;
read-prestages)
    command=(
        "${command_base[@]}"
        read
        --type "computer_prestage"
        --all
    )
;;
read-device-prestages)
    command=(
        "${command_base[@]}"
        read
        --type "mobile_device_prestage"
        --all
    )
;;
category)
    command=(
        "${command_base[@]}"
        category
        --name JamfUploadTest
        --priority 18
        --replace
    )
;;
group)
    command=(
        "${command_base[@]}"
        group
        --name "Firefox & stuff test users"
        --template "templates/SmartGroupTemplate-test-users.xml"
        --key POLICY_NAME="Firefox & stuff"
        --replace
    )
;;
delete-group)
    command=(
        "${command_base[@]}"
        delete
        --type "computer_group"
        --name "1Password-update-smart"
    )
;;
delete-script)
    command=(
        "${command_base[@]}"
        delete
        --type "script"
        --name "EndNote-postinstall.sh"
    )
;;
delete-pkg)
    command=(
        "${command_base[@]}"
        delete
        --type "package"
        --name "$pkg_path"
    )
;;
mobiledevicegroup)
    command=(
        "${command_base[@]}"
        mobiledevicegroup
        --name "Allow Screen Recording"
        --template "templates/AllowScreenRecording-mobiledevicegroup.xml"
        --key GROUP_NAME="Allow Screen Recording"
        --key TESTING_GROUP_NAME="Testing"
        --key custom_curl_opts="--max-time 3600"
        --replace
    )
;;
msu)
    command=(
        "${command_base[@]}"
        msu
        --device-type "computer"
        --group "Testing"
        --version "latest-minor"
        --days "14"
    )
;;
payload)
    command=(
        "${command_base[@]}"
        profile
        --name "Carbon Copy Cloner"
        --template "templates/ProfileTemplate-1-group-1-exclusion.xml"
        --payload "templates/com.bombich.ccc.plist"
        --identifier com.bombich.ccc
        --category JamfUploadTest
        --organization "Graham Pugh Inc."
        --description "Amazing test profile"
        --computergroup "Testing"
        --key REGISTRATION_CODE="FAKE-CODE"
        --key REGISTRATION_EMAIL="yes@yes.com"
        --key REGISTRATION_NAME="ETH License Administration"
        --key REGISTRATION_PRODUCT_NAME='Carbon Copy Cloner 6 Volume License'
        --key EXCLUSION_GROUP_NAME="Firefox test users"
        --replace
    )
;;
profile)
    command=(
        "${command_base[@]}"
        profile
        --template "templates/ProfileTemplate-test-users.xml"
        --category JamfUploadTest
        --computergroup "Testing"
        --mobileconfig "templates/TestProfileIdentifiers.mobileconfig"
        --replace
    )
;;
profile2)
    command=(
        "${command_base[@]}"
        profile
        --template "templates/ProfileTemplate-test-users.xml"
        --category JamfUploadTest
        --computergroup "Testing"
        --mobileconfig "templates/MicrosoftAutoUpdate-notifications.mobileconfig"
        --key PROFILE_NAME="Microsoft AutoUpdate Notifications"
        --key PROFILE_DESCRIPTION="Enables notifications for Microsoft AutoUpdate"
        --key ORGANIZATION="Microsoft"
        --replace
    )
;;
profile_retain_scope)
    command=(
        "${command_base[@]}"
        profile
        --template "templates/ProfileTemplate-test-users.xml"
        --category JamfUploadTest
        --computergroup "Testing"
        --mobileconfig "templates/MicrosoftAutoUpdate-notifications.mobileconfig"
        --key PROFILE_NAME="Microsoft AutoUpdate Notifications"
        --key PROFILE_DESCRIPTION="Enables notifications for Microsoft AutoUpdate"
        --key ORGANIZATION="Microsoft"
        --replace
        --retain-existing-scope
    )
;;
ea)
    command=(
        "${command_base[@]}"
        ea
        --name "Microsoft AutoUpdate Version"
        --script "templates/MicrosoftAutoUpdate-EA.sh"
        --replace
    )
;;
ea-popup)
    command=(
        "${command_base[@]}"
        ea
        --name "Test Popup"
        --type "popup"
        --choices "1.0,1.1,1.2,1.3"
        --description "Choose a version"
        --inventory-display "General"
        --replace
    )
;;
mea-popup)
    command=(
        "${command_base[@]}"
        mobiledeviceea
        --name "Test Popup"
        --type "popup"
        --choices "1.0,1.1,1.2,1.3"
        --description "Choose a version"
        --inventory-display "General"
        --replace
    )
;;
macapp)
    command=(
        "${command_base[@]}"
        macapp
        --name "Bitwarden"
        --template "templates/MacApp-allcomputers.xml"
        --key CATEGORY="JSPP - Applications"
        --key DEPLOYMENT_TYPE="Make Available in Self Service"
        --replace
    )
;;
macapp2)
    command=(
        "${command_base[@]}"
        macapp
        --name "Bitwarden - auto-install"
        --clone-from "Bitwarden"
        --template "templates/MacApp-noscope-autoinstall.xml"
        --key CATEGORY="JSPP - Applications"
        --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install"
        --replace
    )
;;
mobiledeviceappauto)
    command=(
        "${command_base[@]}"
        mobiledeviceapp
        --name "Bitwarden Password Manager - Automatic"
        --clone-from "Bitwarden Password Manager"
        --template "templates/MobileDeviceApp-noscope-autoinstall.xml"
        --key CATEGORY="JSPP - Applications"
        --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install"
        --replace
    )
;;
mobiledeviceappautoconfig)
    command=(
        "${command_base[@]}"
        mobiledeviceapp
        --name "Bitwarden Password Manager - Automatic"
        --clone-from "Bitwarden Password Manager"
        --template "templates/MobileDeviceApp-noscope-autoinstall.xml"
        --appconfig "templates/AppConfig.xml"
        --key CATEGORY="Applications"
        --key DEPLOYMENT_TYPE="Install Automatically/Prompt Users to Install"
        --replace
    )
;;
mobiledeviceappselfservice)
    command=(
        "${command_base[@]}"
        mobiledeviceapp
        --name "Bitwarden Password Manager"
        --template "templates/MobileDeviceApp-noscope.xml"
        --key CATEGORY="JSPP - Applications"
        --key DEPLOYMENT_TYPE="Make Available in Self Service"
        --replace
    )
;;
mobiledeviceappselfserviceconfig)
    command=(
        "${command_base[@]}"
        mobiledeviceapp
        --name "Bitwarden Password Manager"
        --template "templates/MobileDeviceApp-noscope.xml"
        --appconfig "templates/AppConfig.xml"
        --key CATEGORY="JSPP - Applications"
        --key DEPLOYMENT_TYPE="Make Available in Self Service"
        --replace
    )
;;
mobiledeviceapp-fromread)
    command=(
        "${command_base[@]}"
        mobiledeviceapp
        --name "Jamf Self Service"
        --template "/Users/Shared/Jamf/JamfUploaderTests/MobileDeviceApp-Template-JamfSelfService.xml"
        --replace
    )
;;
mobiledeviceprofile)
    command=(
        "${command_base[@]}"
        mobiledeviceprofile
        --template "templates/MobileDeviceProfileTemplate-test-users.xml"
        --category JamfUploadTest
        --mobiledevicegroup "Testing"
        --mobileconfig "templates/AllowScreenRecording.mobileconfig"
        --replace
    )
;;
policy)
    command=(
        "${command_base[@]}"
        policy
        --name "Install plistyamlplist"
        --template "templates/PolicyTemplate-trigger.xml"
        --key POLICY_NAME="Install plistyamlplist"
        --key TRIGGER_NAME="plistyamlplist-install"
        --key CATEGORY="JamfUploadTest"
        --key pkg_name="$pkg_name"
        --replace
    )
;;
policy-retain-scope)
    command=(
        "${command_base[@]}"
        policy
        --name "Install Authy Desktop"
        --template "templates/PolicyTemplate-trigger.xml"
        --key POLICY_NAME="Install Authy Desktop"
        --key TRIGGER_NAME="Authy Desktop-install"
        --key CATEGORY="JamfUploadTest"
        --key pkg_name="Authy Desktop-1.8.4.pkg"
        --replace
        --retain-existing-scope
    )
;;
prestage)
    command=(
        "${command_base[@]}"
        computerprestage
        --name "Test PreStage 3"
        --template "templates/computer-prestage-example.json"
        --replace
    )
;;
prestage2)
    command=(
        "${command_base[@]}"
        computerprestage
        --name "Test PreStage with Account"
        --template "templates/computer-prestage-example-account.json"
        --replace
    )
;;
account)
    command=(
        "${command_base[@]}"
        account
        --name "Test Group"
        --type "group"
        --template "templates/Account-Group-local.xml"
    )
;;
account2)
    command=(
        "${command_base[@]}"
        account
        --name "graham"
        --type "user"
        --template "templates/Account-User-groupaccess.xml"
        --key ACCOUNT_FULLNAME="Graham Pugh Test Account"
        --key ACCOUNT_PASSWORD="GrahamsPassword"
        --key ACCOUNT_EMAIL="graham@pugh.com"
        --key GROUP_NAME="Test Group"
    )
;;
account3)
    command=(
        "${command_base[@]}"
        account
        --name "graham"
        --type "user"
        --template "templates/Account-User-fullaccess.xml"
        --key ACCOUNT_FULLNAME="Graham Pugh Test Account"
        --key ACCOUNT_EMAIL="graham@pugh.com"
        --replace
    )
;;
restriction)
    command=(
        "${command_base[@]}"
        restriction
        --name "Restrict Carbon Copy Cloner"
        --template "templates/RestrictionTemplate-singlegroup.xml"
        --process_name "Carbon Copy Cloner"
        --display_message "Carbon Copy Cloner is not allowed."
        --match_exact_process_name
        --kill_process
        --computergroup Testing
        --replace
    )
;;
script)
    command=(
        "${command_base[@]}"
        script
        --name "Microsoft Office License Type.sh"
        --script "templates/Microsoft Office License Type.sh"
        --script_parameter4 "License Type"
        --replace
    )
;;
patch)
    command=(
        "${command_base[@]}"
        patch
        --name "Installomator"
        --title "Installomator"
        --policy-name "Install Latest Installomator"
        --template "templates/PatchTemplate-selfservice.xml"
        --pkg-name "Installomator-10.5.pkg"
        --version "10.5"
        "$url"
        --replace
    )
;;
patch2)
    command=(
        "${command_base[@]}"
        patch
        --name "Firefox"
        --title "Firefox"
        --template "templates/PatchTemplate-selfservice.xml"
        --pkg-name "Firefox-96.0.pkg"
        --version "96.0"
        --policy-name "Install Latest Firefox"
        --key PATCH_ENABLED="true"
        --replace
    )
;;
patchcheck)
    command=(
        "${command_base[@]}"
        patchcheck
        --title "Firefox"
        --pkg-name "Firefox-96.0.pkg"
        --version "96.0"
        --replace
    )
;;
pkg)
    command=(
        "${command_base[@]}"
        pkg
        --pkg "$pkg_path"
        --category "JamfUploadTest"
        --info "Uploaded directly by JamfPackageUploader using v1/packages"
        --notes "$(date)"
        --replace
    )
;;
pkg-plus-calc*)
    command=(
        "${command_base[@]}"
        pkg
        --pkg "$pkg_path"
        --category "JamfUploadTest"
        --info "Uploaded directly by JamfPackageUploader using v1/packages"
        --notes "$(date)"
        --recalculate
        --replace
    )
;;
dock)
    command=(
        "${command_base[@]}"
        dock
        --name "ETH Self Service"
        --type "App"
        --path "/Applications/ETH Self Service.app/"
        --replace
    )
;;
icon)
    command=(
        "${command_base[@]}"
        icon
        --icon-uri "https://ics.services.jamfcloud.com/icon/hash_13139b4d9732a8b2fa3bbe25e6c6373e8ef6b85a7c7ba2bd15615195d63bc648"
    )
;;
icon2)
    command=(
        "${command_base[@]}"
        icon
        --icon "/tmp/Apple Configurator.png"
    )
;;
apirole)
    command=(
        "${command_base[@]}"
        apirole
        --name "JamfUploader Test API Role"
        --template "templates/APIRoleTemplate-example.json"
        --replace
    )
;;
apiclient)
    command=(
        "${command_base[@]}"
        apiclient
        --name "JamfUploader Test API Client"
        --api-role-name "JamfUploader Test API Role"
        --lifetime "150"
        --enabled
        --replace
    )
;;
delete-policy)
    command=(
        "${command_base[@]}"
        policydelete
        --name "Install Latest Adium"
    )
;;
policyflush)
    command=(
        "${command_base[@]}"
        policyflush
        --name "0001 - Install Rosetta 2"
        --interval "Zero Days"
    )
;;
pkg-noreplace)
    command=(
        "${command_base[@]}"
        pkg
        --pkg "$pkg_path"
        --pkg-name "$(basename "$pkg_path")"
        --name "$(basename "$pkg_path")"
        --category JamfUploadTest
        --info "Uploaded directly by JamfPackageUploader using v1/packages"
        --notes "$(date)"
    )
;;
pkg-aws)
    command=(
        "${command_base[@]}"
        pkg
        --pkg "$pkg_path"
        --pkg-name "$(basename "$pkg_path")"
        --name "$(basename "$pkg_path")"
        --category "Testing"
        --info "Uploaded directly by JamfPackageUploader in AWS-CLI mode"
        --aws
        --key "S3_BUCKET_NAME=jamf2360b29f101f4e0881cf6422ee2be25e"
        --replace
    )
;;
pkgclean)
    command=(
        "${command_base[@]}"
        pkgclean
        --keep "0"
        --key "NAME=gen-pkg-lightspeed"
    )
;;
unusedpkg)
    command=(
        "${command_base[@]}"
        unusedpkgclean
        --slack-url "$slack_webhook_url"
    )
;;
    # --dry-run \
pkgcalc)
    command=(
        "${command_base[@]}"
        pkgcalc
    )
;;
pkgdata)
    command=(
        "${command_base[@]}"
        pkgdata
        --pkg-name "$(basename "$pkg_path")"
        --name "$(basename "$pkg_path")"
        --category JamfUploadTest
        --info "Updated by JamfPkgMetadataUploader"
        --notes "$(date)"
        --replace
    )
;;
jira)
    command=(
        "${command_base[@]}"
        jira
        --name "JamfUploaderJiraIssueCreator Test - please ignore"
        --policy-name "JamfUploaderJiraIssueCreator Test"
        --policy-category "Applications"
        --pkg-category "Packages"
        --pkg-name "Test-Package.pkg"
        --patch-name "Test Patch Policy"
        --version "1.2.3"
        --patch-uploaded
        --pkg-uploaded
        --policy-uploaded
        --jira-user "$jira_user"
        --jira-project "$jira_project"
        --jira-priority "5"
        --jira-issue "10001"
        --jira-api-token "$jira_api_token"
        --jira-url "$url/rest/api/3/issue/"
    )
;;
slack)
    command=(
        "${command_base[@]}"
        slack
        --name "JamfUploaderSlacker Test - please ignore"
        --policy-name "JamfUploaderSlacker Test"
        --policy-category "Applications"
        --pkg-category "Packages"
        --pkg-name "Test-Package.pkg"
        --version "1.2.3"
        --pkg-uploaded
        --policy-uploaded
        --slack-user "JamfUploader Test User"
        --slack-url "$slack_webhook_url"
        --icon "https://resources.jamf.com/images/logos/Jamf-Icon-color.png"
    )
;;
teams)
    command=(
        "${command_base[@]}"
        teams
        --name "JamfUploaderTeamsNotifier Test - please ignore"
        --policy-name "JamfUploaderTeamsNotifier Test"
        --policy-category "Applications"
        --pkg-category "Packages"
        --pkg-name "Test-Package.pkg"
        --version "1.2.3"
        --pkg-uploaded
        --policy-uploaded
        --teams-user "JamfUploader Test User"
        --icon "https://resources.jamf.com/images/logos/Jamf-Icon-color.png"
        --patch-uploaded
        --patch-name "Test Patch Policy"
    )
;;
skip)
    command=(
        "${command_base[@]}"
        obj
        --type "policy"
        --template "templates/PolicyTemplate-trigger.xml"
        --key POLICY_NAME="Install plistyamlplist"
        --key TRIGGER_NAME="plistyamlplist-install"
        --key CATEGORY="JamfUploadTest"
        --key pkg_name="$pkg_name"
        --skip
    )
    ;;
*)
    echo "Unknown test type: $test_type"
    echo "Usage: test.sh [test_type]"
    exit 1
;;
esac

# now print out the command that will be executed, and run the command
printf '%s\n' "Executing command: $(printf '%s ' "${command[@]}")"
"${command[@]}"

if [[ $open_results ]]; then
    open "/Users/Shared/Jamf/JamfUploaderTests"
fi


# revert url
if [[ $usual_url ]]; then
    defaults write "$prefs" JSS_URL "$usual_url"
fi
