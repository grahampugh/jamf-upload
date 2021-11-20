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
    pkg | package
    policy
    restriction | softwarerestriction
    script

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

Extension Attribute arguments:
    --name <string>         The name
    --script <path>         Full path of the script to be uploaded
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Package arguments:
    --name <string>         The name
    --pkg <path>            Full path to the package to uplaod
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

Policy arguments:
    --name <string>         The name
    --template <path>       XML template
    --icon <path>           Full path to an icon file for Self Service policies
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item
    --replace-icon          Set to replace the existing icon if it has the same name

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
    --process_name          Process name to restrict
    --display_message       Message to display to users when the restriction is invoked
    --match_exact_process_name
                            Match only the exact process name if True
    --send_notification     Send a notification when the restriction is invoked if True
    --kill_process          Kill the process when the restriction is invoked if True
    --delete_executable     Delete the executable when the restriction is invoked if True
    --replace               Replace existing item
"
}

##############
## DEFAULTS ##
##############

temp_processor_plist="/tmp/processor.plist"
temp_receipt="/tmp/processor_receipt.plist"

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
elif [[ $object == "ea" || $object == "extensionattribute" ]]; then
    processor="JamfExtensionAttributeUploader"
elif [[ $object == "pkg" || $object == "package" ]]; then
    processor="JamfPackageUploader"
elif [[ $object == "policy" ]]; then
    processor="JamfPolicyUploader"
elif [[ $object == "restriction" || $object == "softwarerestriction" ]]; then
    processor="JamfSoftwareRestrictionUploader"
elif [[ $object == "script" ]]; then
    processor="JamfScriptUploader"
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
            elif [[ $processor == "JamfPackageUploader" ]]; then
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
                if defaults write "$temp_processor_plist" replace_computergroup "True"; then
                    echo "   [jamf-upload] Wrote replace_computergroup='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_profile "True"; then
                    echo "   [jamf-upload] Wrote replace_profile='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_ea "True"; then
                    echo "   [jamf-upload] Wrote replace_ea='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_pkg "True"; then
                    echo "   [jamf-upload] Wrote replace_pkg='True' into $temp_processor_plist"
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
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if defaults write "$temp_processor_plist" ea_name "$1"; then
                    echo "   [jamf-upload] Wrote ea_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" pkg_name "$1"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" reboot_required "$1"; then
                    echo "   [jamf-upload] Wrote reboot_required='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --os_requirement*|--os-requirement*|--osrequirement*)  
            ## allows --os_requirement, --os-requirement, --osrequirements
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" os_requirement "$1"; then
                    echo "   [jamf-upload] Wrote os_requirement='$1' into $temp_processor_plist"
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
        --icon)
            shift
            if [[ $processor == "JamfPolicyUploader" ]]; then
                if defaults write "$temp_processor_plist" icon "$1"; then
                    echo "   [jamf-upload] Wrote icon='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --replace_icon|--replace-icon) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if defaults write "$temp_processor_plist" replace_icon "True"; then
                    echo "   [jamf-upload] Wrote replace_icon='True' into $temp_processor_plist"
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

# this folder
DIR=$(dirname "$0")

if [[ $verbosity -le 1 ]]; then
    # Run the custom processor and output to file
    /Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 "$DIR/JamfUploaderProcessors/$processor.py" < "$temp_processor_plist" > "$temp_receipt"
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
    /Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 "$DIR/JamfUploaderProcessors/$processor.py" < "$temp_processor_plist"
fi
