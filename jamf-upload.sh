#!/bin/bash

:<<DOC
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
    category
    group | computergroup
    profile | computerprofile
    ea | extensionattribute
    logflush
    patch
    pkg | package
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
    --recipe-dir <RECIPE_DIR>

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

Package arguments:
    --name <string>         The name
    --pkg <path>            Full path to the package to upload
    --priority <int>        The priority
    --category <string>     The category. Must exist.
    --smb-url <url>         URL of the fileshare distribution point (on prem only)
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
    --replace               Replace existing item
    --jcds                  Use v3 API for package upload to JCDS 

Policy arguments:
    --name <string>         The name
    --template <path>       XML template
    --icon <path>           Full path to an icon file for Self Service policies
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item
    --replace-icon          Set to replace the existing icon if it has the same name

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

echo "" > "$temp_processor_plist"  # ensure an empty processor at the start of the run

# set default for RECIPE_DIR (required for templates)
if defaults write "$temp_processor_plist" RECIPE_DIR "."; then
    echo "   [jamf-upload] Wrote RECIPE_DIR='.' into $temp_processor_plist"
fi


object="$1"
if [[ $object == "category" ]]; then 
    processor="JamfCategoryUploader"
elif [[ $object == "group" || $object == "computergroup" ]]; then
    processor="JamfComputerGroupUploader"
elif [[ $object == "profile" || $object == "computerprofile" ]]; then
    processor="JamfComputerProfileUploader"
elif [[ $object == "dock" || $object == "dockitem" ]]; then
    processor="JamfDockItemUploader"
elif [[ $object == "ea" || $object == "extensionattribute" ]]; then
    processor="JamfExtensionAttributeUploader"
elif [[ $object == "pkg" || $object == "package" ]]; then
    processor="JamfPackageUploader"
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
            if defaults write "$temp_processor_plist" ''"$(defaults read "$autopkg_prefs")"''; then
                echo "   [jamf-upload] Wrote autopkg prefs into $temp_processor_plist"
            fi
            ;;
        -v*)
            verbose="${#1}"
            verbosity=$(( verbose-1 ))
            if defaults write "$temp_processor_plist" verbose -int $verbosity; then
                echo "   [jamf-upload] Wrote verbose='$verbosity' into $temp_processor_plist"
            fi
            ;;
        --url) 
            shift
            if defaults write "$temp_processor_plist" JSS_URL "$1"; then
                echo "   [jamf-upload] Wrote JSS_URL='$1' into $temp_processor_plist"
            fi
            ;;
        --recipe-dir) 
            shift
            if defaults write "$temp_processor_plist" RECIPE_DIR "$1"; then
                echo "   [jamf-upload] Wrote RECIPE_DIR='$1' into $temp_processor_plist"
            fi
            ;;
        --user*)  
            ## allows --user or --username
            shift
            if defaults write "$temp_processor_plist" API_USERNAME "$1"; then
                echo "   [jamf-upload] Wrote API_USERNAME='$1' into $temp_processor_plist"
            fi
            ;;
        --pass*)  
            ## allows --pass or --password
            shift
            if defaults write "$temp_processor_plist" API_PASSWORD "$1"; then
                echo "   [jamf-upload] Wrote API_PASSWORD='[redacted]' into $temp_processor_plist"
            fi
            ;;
        --priority) 
            shift
            if [[ $processor == "JamfCategoryUploader" ]]; then
                if defaults write "$temp_processor_plist" category_priority "$1"; then
                    echo "   [jamf-upload] Wrote category_priority='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" pkg_priority "$1"; then
                    echo "   [jamf-upload] Wrote pkg_priority='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_priority "$1"; then
                    echo "   [jamf-upload] Wrote script_priority='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace) 
            if [[ $processor == "JamfCategoryUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_category "True"; then
                    echo "   [jamf-upload] Wrote replace_category='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_group "True"; then
                    echo "   [jamf-upload] Wrote replace_group='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_profile "True"; then
                    echo "   [jamf-upload] Wrote replace_profile='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_dock_item "True"; then
                    echo "   [jamf-upload] Wrote replace_dock_item='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_ea "True"; then
                    echo "   [jamf-upload] Wrote replace_ea='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" replace_pkg "True"; then
                    echo "   [jamf-upload] Wrote replace_pkg='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_patch "True"; then
                    echo "   [jamf-upload] Wrote replace_patch='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_policy "True"; then
                    echo "   [jamf-upload] Wrote replace_policy='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_restriction "True"; then
                    echo "   [jamf-upload] Wrote replace_restriction='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_script "True"; then
                    echo "   [jamf-upload] Wrote replace_script='True' into $temp_processor_plist"
                fi
            fi
            ;;
        -n|--name) 
            shift
            if [[ $processor == "JamfCategoryUploader" ]]; then
                if defaults write "$temp_processor_plist" category_name "$1"; then
                    echo "   [jamf-upload] Wrote category_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" ]]; then
                if defaults write "$temp_processor_plist" computergroup_name "$1"; then
                    echo "   [jamf-upload] Wrote computergroup_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" profile_name "$1"; then
                    echo "   [jamf-upload] Wrote profile_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if defaults write "$temp_processor_plist" dock_item_name "$1"; then
                    echo "   [jamf-upload] Wrote dock_item_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if defaults write "$temp_processor_plist" ea_name "$1"; then
                    echo "   [jamf-upload] Wrote ea_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" pkg_name "$1"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" patch_name "$1"; then
                    echo "   [jamf-upload] Wrote patch_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" || $processor == "JamfPolicyDeleter" || $processor == "JamfPolicyLogFlusher" ]]; then
                if defaults write "$temp_processor_plist" policy_name "$1"; then
                    echo "   [jamf-upload] Wrote policy_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" restriction_name "$1"; then
                    echo "   [jamf-upload] Wrote restriction_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_name "$1"; then
                    echo "   [jamf-upload] Wrote script_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" NAME "$1"; then
                    echo "   [jamf-upload] Wrote NAME='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --template) 
            shift
            if [[ $processor == "JamfComputerGroupUploader" ]]; then
                if defaults write "$temp_processor_plist" computergroup_template "$1"; then
                    echo "   [jamf-upload] Wrote computergroup_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" profile_template "$1"; then
                    echo "   [jamf-upload] Wrote profile_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" patch_template "$1"; then
                    echo "   [jamf-upload] Wrote patch_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if defaults write "$temp_processor_plist" policy_template "$1"; then
                    echo "   [jamf-upload] Wrote policy_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" restriction_template "$1"; then
                    echo "   [jamf-upload] Wrote restriction_template='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --payload)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" payload "$1"; then
                    echo "   [jamf-upload] Wrote payload='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --mobileconfig)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" mobileconfig "$1"; then
                    echo "   [jamf-upload] Wrote mobileconfig='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --identifier)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" identifier "$1"; then
                    echo "   [jamf-upload] Wrote identifier='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --category)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" profile_category "$1"; then
                    echo "   [jamf-upload] Wrote profile_category='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" pkg_category "$1"; then
                    echo "   [jamf-upload] Wrote pkg_category='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_category "$1"; then
                    echo "   [jamf-upload] Wrote script_category='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --organization)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" organization "$1"; then
                    echo "   [jamf-upload] Wrote organization='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --description)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" profile_description "$1"; then
                    echo "   [jamf-upload] Wrote profile_description='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --computergroup)
            shift
            if [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" profile_computergroup "$1"; then
                    echo "   [jamf-upload] Wrote profile_computergroup='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" restriction_computergroup "$1"; then
                    echo "   [jamf-upload] Wrote restriction_computergroup='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --path)
            shift
            if [[ $processor == "JamfDockItemUploader" ]]; then
                if defaults write "$temp_processor_plist" dock_item_path "$1"; then
                    echo "   [jamf-upload] Wrote dock_item_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --type)
            shift
            if [[ $processor == "JamfDockItemUploader" ]]; then
                if defaults write "$temp_processor_plist" dock_item_type "$1"; then
                    echo "   [jamf-upload] Wrote dock_item_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --script|--script_path)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if defaults write "$temp_processor_plist" ea_script_path "$1"; then
                    echo "   [jamf-upload] Wrote ea_script_path='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_path "$1"; then
                    echo "   [jamf-upload] Wrote script_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_url|--smb-url)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" SMB_URL "$1"; then
                    echo "   [jamf-upload] Wrote SMB_URL='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_user*|--smb-user*)  
            ## allows --smb_user, --smb_username, --smb-user, --smb-username
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" SMB_USERNAME "$1"; then
                    echo "   [jamf-upload] Wrote SMB_USERNAME='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_pass*)  
            ## allows --smb_pass, --smb_password, --smb-pass, --smb-password
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" SMB_PASSWORD "$1"; then
                    echo "   [jamf-upload] Wrote SMB_PASSWORD='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg|--pkg_path)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" pkg_path "$1"; then
                    echo "   [jamf-upload] Wrote pkg_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --info)
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" pkg_info "$1"; then
                    echo "   [jamf-upload] Wrote pkg_info='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_info "$1"; then
                    echo "   [jamf-upload] Wrote script_info='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --notes)
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" pkg_notes "$1"; then
                    echo "   [jamf-upload] Wrote pkg_notes='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" script_notes "$1"; then
                    echo "   [jamf-upload] Wrote script_notes='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --reboot_required|--reboot-required) 
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPackageUploaderGUI" ]]; then
                if defaults write "$temp_processor_plist" reboot_required "$1"; then
                    echo "   [jamf-upload] Wrote reboot_required='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --os_requirement*|--os-requirement*|--osrequirement*)  
            ## allows --os_requirement, --os-requirement, --osrequirements
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" os_requirements "$1"; then
                    echo "   [jamf-upload] Wrote os_requirements='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" osrequirements "$1"; then
                    echo "   [jamf-upload] Wrote osrequirements='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --required_processor|--required-processor)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" required_processor "$1"; then
                    echo "   [jamf-upload] Wrote required_processor='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --send_notification|--send-notification) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" send_notification -string "true"; then
                    echo "   [jamf-upload] Wrote send_notification='true' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" restriction_send_notification -string "true"; then
                    echo "   [jamf-upload] Wrote restriction_send_notification='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace_pkg_metadata|--replace-pkg-metadata) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_pkg_metadata "true"; then
                    echo "   [jamf-upload] Wrote replace_pkg_metadata='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --jcds) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" jcds_mode "true"; then
                    echo "   [jamf-upload] Wrote jcds_mode='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --title)
            shift
            if [[ $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" patch_softwaretitle "$1"; then
                    echo "   [jamf-upload] Wrote patch_softwaretitle='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-name)
            shift
            if [[ $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" patch_icon_policy_name "$1"; then
                    echo "   [jamf-upload] Wrote patch_icon_policy_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" policy_name "$1"; then
                    echo "   [jamf-upload] Wrote policy_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --version) 
            shift
            if [[ $processor == "JamfPatchUploader" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" version "$1"; then
                    echo "   [jamf-upload] Wrote version='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --icon)
            shift
            if [[ $processor == "JamfPolicyUploader" ]]; then
                if defaults write "$temp_processor_plist" icon "$1"; then
                    echo "   [jamf-upload] Wrote icon='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderSlacker" ]]; then
                if defaults write "$temp_processor_plist" slack_icon_url "$1"; then
                    echo "   [jamf-upload] Wrote slack_icon_url='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" teams_icon_url "$1"; then
                    echo "   [jamf-upload] Wrote teams_icon_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace_icon|--replace-icon) 
            if [[ $processor == "JamfPolicyUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_icon "True"; then
                    echo "   [jamf-upload] Wrote replace_icon='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --interval)
            shift
            if [[ $processor == "JamfPolicyLogFlusher" ]]; then
                if defaults write "$temp_processor_plist" logflush_interval "$1"; then
                    echo "   [jamf-upload] Wrote logflush_interval='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --script_parameter*)
            param_number="${key_value_pair#--script_parameter}"
            shift
            if [[ $processor == "JamfScriptUploader" ]]; then
                if defaults write "$temp_processor_plist" "script_parameter$param_number" "$1"; then
                    echo "   [jamf-upload] Wrote script_parameter$param_number='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --process_name|--process-name) 
            shift
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" process_name "$1"; then
                    echo "   [jamf-upload] Wrote process_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --display_message|--display-message) 
            shift
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" display_message "$1"; then
                    echo "   [jamf-upload] Wrote display_message='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --match_exact_process_name|--match-exact-process-name) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" match_exact_process_name -string "true"; then
                    echo "   [jamf-upload] Wrote match_exact_process_name='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --kill_process|--kill-process) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" kill_process -string "true"; then
                    echo "   [jamf-upload] Wrote kill_process='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --delete_executable|--delete-executable) 
            if [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if defaults write "$temp_processor_plist" delete_executable -string "true"; then
                    echo "   [jamf-upload] Wrote delete_executable='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-category)
            shift
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" PKG_CATEGORY "$1"; then
                    echo "   [jamf-upload] Wrote PKG_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-category)
            shift
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" POLICY_CATEGORY "$1"; then
                    echo "   [jamf-upload] Wrote POLICY_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-name) 
            shift
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" || $processor == "JamfPatchUploader" ]]; then
                if defaults write "$temp_processor_plist" pkg_name "$1"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            fi
           ;;
        --patch-uploaded) 
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" jamfpatchuploader_summary_result -string "true"; then
                    echo "   [jamf-upload] Wrote jamfpatchuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-uploaded) 
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" jamfpackageuploader_summary_result -string "true"; then
                    echo "   [jamf-upload] Wrote jamfpackageuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-uploaded) 
            if [[ $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" jamfpolicyuploader_summary_result -string "true"; then
                    echo "   [jamf-upload] Wrote jamfpolicyuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --slack-url) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if defaults write "$temp_processor_plist" slack_webhook_url "$1"; then
                    echo "   [jamf-upload] Wrote slack_webhook_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --slack-user) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if defaults write "$temp_processor_plist" slack_username "$1"; then
                    echo "   [jamf-upload] Wrote slack_username='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --channel) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if defaults write "$temp_processor_plist" slack_channel "$1"; then
                    echo "   [jamf-upload] Wrote slack_channel='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --emoji) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if defaults write "$temp_processor_plist" slack_icon_emoji "$1"; then
                    echo "   [jamf-upload] Wrote slack_icon_emoji='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --teams-url) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" teams_webhook_url "$1"; then
                    echo "   [jamf-upload] Wrote teams_webhook_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --teams-user) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" teams_username "$1"; then
                    echo "   [jamf-upload] Wrote teams_username='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --patch_name) 
            shift
            if [[ $processor == "JamfUploaderTeamsNotifier" ]]; then
                if defaults write "$temp_processor_plist" patch_name "$1"; then
                    echo "   [jamf-upload] Wrote patch_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --key)
            shift
            key_value_pair="$1"
            key="${key_value_pair%%=*}"
            value="${key_value_pair#$key=}"
            if defaults write "$temp_processor_plist" "$key" "$value"; then
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
