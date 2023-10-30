#!/bin/bash

: <<DOC
A wrapper script for running the JamfUploader processors in a standalone fashion, without running an AutoPkg recipe.
DOC

###########
## USAGE ##
###########

usage() {
    echo "
Usage: 
./jamf-upload.sh [object_type] [--help] [arguments]

Valid object types:
    account
    category
    group | computergroup
    mobiledevicegroup
    profile | computerprofile
    mobiledeviceprofile
    ea | extensionattribute
    icon
    ldap_server
    logflush
    macapp
    patch
    pkg | package
    pkgclean
    policy
    restriction | softwarerestriction
    script
    slack
    teams

Arguments:
    --prefs <path>          Inherit AutoPkg prefs file provided by the full path to the file
    -v[vvv]                 Set value of verbosity
    --url <JSS_URL>         The Jamf Pro URL
    --user <API_USERNAME>   The API username
    --pass <API_PASSWORD>   The API user's password
    --clientid <ID>         An API Client ID
    --clientsecret <string> An API Client Secret
    --recipe-dir <RECIPE_DIR>

Account arguments:
    --name <string>         The name
    --type <string>         The account type. Must be 'user' or 'group'.
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Category arguments:
    --name <string>         The name
    --priority <int>        The priority
    --replace               Replace existing item

Computer Group arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Computer Profile arguments:
    --name <string>         The name
    --template <path>       XML template
    --payload <path>        A profile payload
    --mobileconfig <path>   A mobileconfig file
    --identifier <string>   Identifier for the profile
    --category <string>     The category. Must exist.
    --organization <string> Organisation for the profile
    --description <string>  Description for the profile
    --computergroup <str>   Computer Group to set as target in the profile
    --key X=Y               Substitutable values in the script. Multiple values can be supplied
    --replace               Replace existing item
    --retain-scope          Retain existing scope when updating an item

Dock Item arguments:
    --name <string>         The name
    --type <string>         Type of Dock Item - either 'App', 'File' or 'Folder'
    --path <string>         Path of Dock Item - e.g. 'file:///Applications/Safari.app/'
    --replace               Replace existing item

Extension Attribute arguments:
    --name <string>         The name
    --script <path>         Full path of the script to be uploaded
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Icon arguments:
    --icon <path>           Full path to an icon file
    --icon-uri <url>        The icon URI from https://ics.services.jamfcloud.com/icon

LDAP Server arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mac App Store App arguments:
    --name <string>         The name
    --cloned-from           The name of the Mac App Store app from which to clone
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mobile Device Group arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mobile Device Profile arguments:
    --name <string>         The name
    --template <path>       XML template
    --mobileconfig <path>   A mobileconfig file
    --identifier <string>   Identifier for the profile
    --category <string>     The category. Must exist.
    --organization <string> Organisation for the profile
    --description <string>  Description for the profile
    --mobiledevicegroup <string>
                            Mobile Device Group to set as target in the profile
    --key X=Y               Substitutable values in the script. Multiple values can be supplied
    --replace               Replace existing item

Package arguments:
    --name <string>         The package display name
    --pkg_name <path>       The package filename
    --pkg <path>            Full path to the package to upload
    --priority <int>        The priority
    --category <string>     The category. Must exist.
    --smb-url <url>         URL of the fileshare distribution point (on premises Jamf Pro only)
    --smb-user <SMB_USERNAME>
                            Username with share access
    --smb_pass <SMB_PASSWORD>
                            Password of the user
    --info <string>         Pkg information field
    --notes <string>        Pkg notes field
    --reboot_required       Set the 'reboot required' option
    --os-requirement <string>
                            Set OS requirement for the pkg
    --required-processor <string>
                            Set CPU type requirement for the pkg
    --send-notification     Set to send a notification when the package is installed
    --replace-pkg-metadata  Set to replace the pkg metadata if no package is uploaded
    --skip-metadata-upload  Set to skip pkg metadata upload
    --replace               Replace existing item
    --jcds                  Use v3 API for package upload to JCDS 
    --jcds2                 Use jcds endpoint for package upload to JCDS 

Package Clean arguments:
    --name <string>         The name to match
    --smb-url <url>         URL of the fileshare distribution point (on premises Jamf Pro only)
    --smb-user <SMB_USERNAME>
                            Username with share access
    --smb_pass <SMB_PASSWORD>
                            Password of the user

Policy arguments:
    --name <string>         The name
    --template <path>       XML template
    --icon <path>           Full path to an icon file for Self Service policies
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item
    --replace-icon          Set to replace the existing icon if it has the same name
    --retain-scope          Retain existing scope when updating an item

Policy Delete arguments:
    --name <string>         The policy name

Policy Log Flush arguments:
    --name <string>         The policy name
    --interval              The log flush interval

Patch Policy arguments:
    --name <string>         The patch policy name
    --pkg <path>            Name of the package to uplaod
    --version <string>      The package (or app) version
    --title <string>        The patch software title
    --template <path>       XML template
    --policy <string>       Name of an existing policy containing the desired icon for the patch policy
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Script arguments:
    --name <string>         The name
    --script <path>         Full path of the script to be uploaded
    --key X=Y               Substitutable values in the script. Multiple values can be supplied
    --script_parameter[4-11]
                            Script parameter labels 
    --replace               Replace existing item

Software Restriction arguments
    --name <string>         The name
    --template <path>       XML template
    --process-name          Process name to restrict
    --display-message       Message to display to users when the restriction is invoked
    --match-exact-process-name
                            Match only the exact process name if True
    --send-notification     Send a notification when the restriction is invoked if True
    --kill-process          Kill the process when the restriction is invoked if True
    --delete-executable     Delete the executable when the restriction is invoked if True
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Slack arguments:
    --name <string>         The name
    --policy-category <string>
                            The POLICY_CATEGORY
    --pkg-category <string> The PKG_CATEGORY
    --pkg_name <string>     The package name
    --version <string>      The package (or app) version
    --pkg-uploaded          Pretends that a package was uploaded (sets a value to jamfpackageuploader_summary_result)
    --policy-uploaded       Pretends that a policy was uploaded (sets a value to jamfpolicyuploader_summary_result)
    --slack-url <url>       The slack_webhook_url
    --slack-user <string>   The Slack user to display
    --icon <url>        The Slack icon URL
    --channel <string>      The Slack channel to post to
    --emoji <string>        the Slack icon emoji

Teams arguments:
    --name <string>         The name
    --policy-category <string>
                            The POLICY_CATEGORY
    --pkg-category <string> The PKG_CATEGORY
    --patch_name <string>   The patch policy name
    --pkg_name <string>     The package name
    --version <string>      The package (or app) version
    --patch-uploaded        Pretends that a patch was updated (sets a value to jamfpatchuploader_summary_result)
    --pkg-uploaded          Pretends that a package was uploaded (sets a value to jamfpackageuploader_summary_result)
    --policy-uploaded       Pretends that a policy was uploaded (sets a value to jamfpolicyuploader_summary_result)
    --teams-url <url>       The teams_webhook_url
    --teams-user <string>   The Teams user to display
    --icon <url>        The Slack icon URL

"
}

##############
## DEFAULTS ##
##############

temp_processor_plist="/tmp/processor.plist"
temp_receipt="/tmp/processor_receipt.plist"

# this folder
DIR=$(dirname "$0")
processors_directory="$DIR/JamfUploaderProcessors"
# processors_directory="$DIR/JamfUploaderProcessorsStandalone"


###############
## ARGUMENTS ##
###############

rm -rf "$temp_processor_plist" # delete any existing file (or folder) at temp_processor_plist path
/usr/libexec/PlistBuddy -c 'Clear dict' "$temp_processor_plist" # ensure an empty processor at the start of the run
# NOTE: DO NOT use "plutil -create" to create a new empty plist since that option is only available on macOS 12 Monterey and newer.

# set default for RECIPE_DIR (required for templates)
if plutil -replace RECIPE_DIR -string "." "$temp_processor_plist"; then
    echo "   [jamf-upload] Wrote RECIPE_DIR='.' into $temp_processor_plist"
fi


object="$1"
if [[ $object == "account" ]]; then 
    processor="JamfAccountUploader"
elif [[ $object == "category" ]]; then 
    processor="JamfCategoryUploader"
elif [[ $object == "group" || $object == "computergroup" ]]; then
    processor="JamfComputerGroupUploader"
elif [[ $object == "profile" || $object == "computerprofile" ]]; then
    processor="JamfComputerProfileUploader"
elif [[ $object == "dock" || $object == "dockitem" ]]; then
    processor="JamfDockItemUploader"
elif [[ $object == "ea" || $object == "extensionattribute" ]]; then
    processor="JamfExtensionAttributeUploader"
elif [[ $object == "icon" ]]; then
    processor="JamfIconUploader"
elif [[ $object == "ldap_server" ]]; then
    processor="JamfClassicAPIObjectUploader"
elif [[ $object == "macapp" ]]; then
    processor="JamfMacAppUploader"
elif [[ $object == "mobiledevicegroup" ]]; then
    processor="JamfMobileDeviceGroupUploader"
elif [[ $object == "mobiledeviceprofile" ]]; then
    processor="JamfMobileDeviceProfileUploader"
elif [[ $object == "pkg" || $object == "package" ]]; then
    processor="JamfPackageUploader"
elif [[ $object == "pkgclean" ]]; then
    processor="JamfPackageCleaner"
elif [[ $object == "pkg-direct" ]]; then
    processor="JamfPackageUploaderGUI"
elif [[ $object == "policy" ]]; then
    processor="JamfPolicyUploader"
elif [[ $object == "policy_delete" ]]; then
    processor="JamfPolicyDeleter"
elif [[ $object == "policy_flush" ]]; then
    processor="JamfPolicyLogFlusher"
elif [[ $object == "patch" ]]; then
    processor="JamfPatchUploader"
elif [[ $object == "restriction" || $object == "softwarerestriction" ]]; then
    processor="JamfSoftwareRestrictionUploader"
elif [[ $object == "script" ]]; then
    processor="JamfScriptUploader"
elif [[ $object == "slack" ]]; then
    processor="JamfUploaderSlacker"
elif [[ $object == "teams" ]]; then
    processor="JamfUploaderTeamsNotifier"
elif [[ $object == "--help" || $object == "help" || $object == "-h" ]]; then
    usage
    exit 0
else
    usage
    exit 1
fi

shift
if [[ ! "$1" ]]; then
    usage
    exit 1
fi

while test $# -gt 0 ; do
    case "$1" in
        --prefs)
            shift
            autopkg_prefs="$1"
            if /usr/libexec/PlistBuddy -c 'Merge /dev/stdin' "$temp_processor_plist" <<< "$(defaults export "$autopkg_prefs" -)"; then # Existing keys in temp_processor_plist will be preserved, only non-existent keys from autopkg_prefs will be added to temp_processor_plist. Any existing duplicate keys WILL NOT be overwritten.
                echo "   [jamf-upload] Wrote autopkg prefs into $temp_processor_plist"
            fi
            ;;
        -v*)
            verbose="${#1}"
            verbosity=$(( verbose-1 ))
            if plutil -replace verbose -integer $verbosity "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote verbose='$verbosity' into $temp_processor_plist"
            fi
            ;;
        --url) 
            shift
            if plutil -replace JSS_URL -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote JSS_URL='$1' into $temp_processor_plist"
            fi
            ;;
        --recipe-dir) 
            shift
            if plutil -replace RECIPE_DIR -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote RECIPE_DIR='$1' into $temp_processor_plist"
            fi
            ;;
        --user*)  
            ## allows --user or --username
            shift
            if plutil -replace API_USERNAME -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote API_USERNAME='$1' into $temp_processor_plist"
            fi
            ;;
        --pass*)  
            ## allows --pass or --password
            shift
            if plutil -replace API_PASSWORD -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote API_PASSWORD='[redacted]' into $temp_processor_plist"
            fi
            ;;
        --clientid)  
            shift
            if plutil -replace CLIENT_ID -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote CLIENT_ID='$1' into $temp_processor_plist"
            fi
            ;;
        --clientsecret)  
            shift
            if plutil -replace CLIENT_SECRET -string "$1" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote CLIENT_SECRET='$1' into $temp_processor_plist"
            fi
            ;;
        --type)
            shift
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace account_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote account_type='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace dock_item_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote dock_item_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --priority) 
            shift
            if [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace category_priority -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote category_priority='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace pkg_priority -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_priority='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_priority -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_priority='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace) 
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace replace_account -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_account='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace replace_category -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_category='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfClassicAPIObjectUploader" ]]; then
                if plutil -replace replace_object -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_object='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" || $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace replace_group -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_group='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace replace_profile -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_profile='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace replace_dock_item -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_dock_item='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if plutil -replace replace_ea -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_ea='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace replace_macapp -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_macapp='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace replace_pkg -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_pkg='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace replace_patch -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_patch='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace replace_policy -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_policy='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace replace_restriction -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_restriction='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace replace_script -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_script='True' into $temp_processor_plist"
                fi
            fi
            ;;
        -n|--name) 
            shift
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace account_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote account_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace category_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote category_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfClassicAPIObjectUploader" ]]; then
                if plutil -replace object_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" ]]; then
                if plutil -replace computergroup_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote computergroup_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace dock_item_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote dock_item_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if plutil -replace ea_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace macapp_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote macapp_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace mobiledevicegroup_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledevicegroup_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace pkg_display_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_display_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageCleaner" ]]; then
                if plutil -replace pkg_name_match -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_name_match='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace patch_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" || $processor == "JamfPolicyDeleter" || $processor == "JamfPolicyLogFlusher" ]]; then
                if plutil -replace policy_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote policy_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace NAME -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote NAME='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --template) 
            shift
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace account_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote account_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfClassicAPIObjectUploader" ]]; then
                if plutil -replace object_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" ]]; then
                if plutil -replace computergroup_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote computergroup_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace macapp_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote macapp_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace mobiledevicegroup_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledevicegroup_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace patch_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace policy_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote policy_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_template='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --payload)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if plutil -replace payload -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote payload='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --mobileconfig)
            shift
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace mobileconfig -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobileconfig='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --identifier)
            shift
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace identifier -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote identifier='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --category)
            shift
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_category -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_category='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace pkg_category -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_category='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_category -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_category='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --organization)
            shift
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace organization -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote organization='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --description)
            shift
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_description -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_description='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --computergroup)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if plutil -replace profile_computergroup -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_computergroup='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_computergroup -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_computergroup='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --retain-existing-scope) 
            if [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace retain_scope -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote retain_scope='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --path)
            shift
            if [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace dock_item_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote dock_item_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --script|--script_path)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if plutil -replace ea_script_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_script_path='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --icon)
            shift
            if [[ $processor == "JamfIconUploader" ]]; then
                if plutil -replace icon_file -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote icon_file='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace icon -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote icon='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_icon_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_icon_url='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace teams_icon_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote teams_icon_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --icon-uri|--icon-url)
            shift
            if [[ $processor == "JamfIconUploader" ]]; then
                if plutil -replace icon_uri -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote icon_uri='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --clone-from|--clone_from)
            shift
            if [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace clone_from -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote clone_from='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --mobiledevicegroup)
            shift
            if [[ $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_mobiledevicegroup -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_mobiledevicegroup='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_url|--smb-url)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace SMB_URL -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_URL='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_user*|--smb-user*)  
            ## allows --smb_user, --smb_username, --smb-user, --smb-username
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace SMB_USERNAME -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_USERNAME='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_pass*)  
            ## allows --smb_pass, --smb_password, --smb-pass, --smb-password
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace SMB_PASSWORD -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_PASSWORD='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg|--pkg_path|--pkg-path)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace pkg_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-name|--pkg_name) 
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" || $processor == "JamfPatchUploader" ]]; then
                if plutil -replace pkg_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            fi
           ;;
        --info)
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace pkg_info -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_info='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_info -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_info='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --notes)
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace pkg_notes -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_notes='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_notes -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_notes='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --reboot_required|--reboot-required) 
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if plutil -replace reboot_required -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote reboot_required='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --os_requirement*|--os-requirement*|--osrequirement*)  
            ## allows --os_requirement, --os-requirement, --osrequirements
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace os_requirements -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote os_requirements='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace osrequirements -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote osrequirements='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --required_processor|--required-processor)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace required_processor -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote required_processor='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --send_notification|--send-notification) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace send_notification -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote send_notification='true' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_send_notification -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_send_notification='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace_pkg_metadata|--replace-pkg-metadata) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace replace_pkg_metadata -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_pkg_metadata='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --skip_metadata_upload|--skip-metadata-upload) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace skip_metadata_upload -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote skip_metadata_upload='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --jcds) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace jcds_mode -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jcds_mode='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --jcds2) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace jcds2_mode -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jcds2_mode='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --keep) 
            shift
            if [[ $processor == "JamfPackageCleaner" ]]; then
                if plutil -replace versions_to_keep -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote versions_to_keep='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --title)
            shift
            if [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace patch_softwaretitle -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_softwaretitle='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-name)
            shift
            if [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace patch_icon_policy_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_icon_policy_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace policy_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote policy_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --version) 
            shift
            if [[ $processor == "JamfPatchUploader" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace version -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote version='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace_icon|--replace-icon) 
            if [[ $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace replace_icon -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_icon='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --interval)
            shift
            if [[ $processor == "JamfPolicyLogFlusher" ]]; then
                if plutil -replace logflush_interval -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote logflush_interval='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --script_parameter*)
            param_number="${key_value_pair#--script_parameter}"
            shift
            if [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace "script_parameter$param_number" -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_parameter$param_number='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --process_name|--process-name) 
            shift
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace process_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote process_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --display_message|--display-message) 
            shift
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace display_message -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote display_message='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --match_exact_process_name|--match-exact-process-name) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace match_exact_process_name -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote match_exact_process_name='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --kill_process|--kill-process) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace kill_process -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote kill_process='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --delete_executable|--delete-executable) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace delete_executable -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote delete_executable='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-category)
            shift
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace PKG_CATEGORY -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote PKG_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-category)
            shift
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace POLICY_CATEGORY -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote POLICY_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --patch-uploaded) 
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpatchuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpatchuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-uploaded) 
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpackageuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpackageuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-uploaded) 
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpolicyuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpolicyuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --slack-url) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_webhook_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_webhook_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --slack-user) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_username -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_username='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --channel) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_channel -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_channel='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --emoji) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_icon_emoji -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_icon_emoji='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --teams-url) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace teams_webhook_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote teams_webhook_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --teams-user) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace teams_username -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote teams_username='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --patch_name) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace patch_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --key)
            shift
            key_value_pair="$1"
            key="${key_value_pair%%=*}"
            value="${key_value_pair#"$key"=}"
            if plutil -replace "$key" -string "$value" "$temp_processor_plist"; then
                echo "   [jamf-upload] Wrote '$key'='$value' into $temp_processor_plist"
            fi
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unused key: $1"
            ;;
    esac
    shift
done

# add the object type for items using the generic JamfClassicAPIObjectUploader processor
if [[ $processor == "JamfClassicAPIObjectUploader" ]]; then
    if plutil -replace object_type -string "$object" "$temp_processor_plist"; then
        echo "   [jamf-upload] Wrote account_type='$object' into $temp_processor_plist"
    fi
fi

echo

###############
## MAIN BODY ##
###############

# Ensure the plist is in XML format
plutil -convert xml1 "$temp_processor_plist"

# Ensure PYHTONPATH includes the AutoPkg libraries
if [[ -d "/Library/AutoPkg" ]]; then
    export PYTHONPATH="/Library/AutoPkg"
else
    echo "ERROR: AutoPkg is not installed"
    exit 1
fi

if [[ $verbosity -le 1 ]]; then
    # Run the custom processor and output to file
    /Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 "$processors_directory/$processor.py" < "$temp_processor_plist" > "$temp_receipt"
    echo
    echo "Output:"
    grep "^$processor" "$temp_receipt" 

    # remove fake output from temp_receipt
    sed -i '' -e "/^$processor/d" "$temp_receipt" 

    echo
    echo "Receipt written to: $temp_receipt"
    echo
else
    echo 
    # Run the custom processor and output to stdout
    /Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 "$processors_directory/$processor.py" < "$temp_processor_plist"
fi
