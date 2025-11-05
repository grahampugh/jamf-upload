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
    apiclient
    apirole
    category
    computerprestage
    delete | objdelete | objectdelete
    group | computergroup
    groupdelete | computergroupdelete
    mobiledevicegroup
    profile | computerprofile
    mobiledeviceprofile
    ea | extensionattribute | computerextensionattribute
    eapopup | eapopupadjuster
    icon
    jira
    logflush
    macapp
    mobiledeviceapp
    msu | managedsoftwareupdateplan
    obj | object | classicobj
    patch
    pkg | package
    pkgdata
    pkgclean
    pkgcalc | packagerecalculate
    policy
    policydelete
    policyflush
    read
    restriction | softwarerestriction
    scope
    script
    slack
    teams
    unusedpkgclean

Arguments:
    --prefs <path>          Inherit AutoPkg prefs file provided by the full path to the file
    -v[vvv]                 Set value of verbosity
    --url <JSS_URL>         The Jamf Pro URL
    --user <API_USERNAME>   The API username
    --pass <API_PASSWORD>   The API user's password
    --clientid <ID>         An API Client ID
    --clientsecret <string> An API Client Secret
    --recipe-dir <RECIPE_DIR>

UPLOAD OPTIONS

Account Upload arguments:
    --name <string>         The name
    --type <string>         The account type. Must be 'user' or 'group'.
    --domain <string>       The LDAP domain name. Must exist.
    --group <string>        The group name. Must exist.
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

API Client Upload arguments:
    --name <string>         The name
    --api-client-id <string>
                            The API Client ID
    --api-role-name <string>
                            The API Role name to assign to the API Client
    --enabled               Enable the API Client
    --lifetime <int>        The lifetime of the API Client in seconds
    --replace               Replace existing item

API Role Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Category Upload arguments:
    --name <string>         The name
    --priority <int>        The priority
    --replace               Replace existing item

Computer Group Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Computer PreStage Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Computer Profile Upload arguments:
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

Dock Item Upload arguments:
    --name <string>         The name
    --type <string>         Type of Dock Item - either 'App', 'File' or 'Folder'
    --path <string>         Path of Dock Item - e.g. 'file:///Applications/Safari.app/'
    --replace               Replace existing item

Computer Extension Attribute Upload arguments:
    --name <string>         The name
    --type <string>         The input type, either 'script', 'text', 'popup', 
                            or 'ldap' (default is 'script')
    --data-type <string>    The data type, either 'string', 'integer', or 'date'. 
                            Only used for 'text' and 'popup' input types. Default is 'string'.
    --description <string>  The description
    --disabled              Disable the EA
    --script <path>         Full path of the script to be uploaded
    --ldap-mapping <string> The Directory Service Attribute Mapping. Musst be a valid mapping.
    --choices               Comma-separated list of values for 'popup' input type. 
                            Must be a comma-separated list.
    --inventory-display <string>
                            The inventory display type. One of GENERAL, HARDWARE, OPERATING_SYSTEM, 
                            USER_AND_LOCATION, PURCHASING, EXTENSION_ATTRIBUTES.
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Generic Object Upload arguments:
    --name <string>         The name
    --id <string>           The ID, can be used instead of --name to specify an ID
    --type <string>         The API object type. This is the name of the key in the XML template.
    --template <path>       XML template
    --output <dir>          Optional directory to output the parsed XML to. Directory must exist.
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Icon Upload arguments:
    --icon <path>           Full path to an icon file
    --icon-uri <url>        The icon URI from https://ics.services.jamfcloud.com/icon

LDAP Server Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mac App Store App Upload arguments:
    --name <string>         The name
    --cloned-from           The name of the Mac App Store app from which to clone
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Managed Software Update Plan Upload arguments:
    --device-type           Device type, one of computer, mobile_device, apple_tv (case insensitive)
    --version-type          Version type, one of latest_minor, latest_major, specific_version (case insensitive)
    --version               Specific version, only required if version_type is set to specific_version
    --group                 Computer or Mobile Device Group name
    --days                  Days until forced install deadline

Mobile Device App Upload arguments:
    --name <string>         The name
    --cloned-from           The name of the Mobile Device app from which to clone
    --template <path>       XML template
    --appconfig <path>      AppConfig file
    --key X=Y               Substitutable values in the template and AppConfig. Multiple values can be supplied
    --replace               Replace existing item

Mobile Device Extension Attribute Upload arguments:
    --name <string>         The name
    --type <string>         The input type, either 'text', 'popup', 
                            or 'ldap' (default is 'script')
    --data-type <string>    The data type, either 'string', 'integer', or 'date'. 
                            Only used for 'text' and 'popup' input types. Default is 'string'.
    --description <string>  The description
    --ldap-mapping <string> The Directory Service Attribute Mapping. Musst be a valid mapping.
    --choices               Comma-separated list of values for 'popup' input type. 
                            Must be a comma-separated list.
    --inventory-display <string>
                            The inventory display type. One of GENERAL, HARDWARE, OPERATING_SYSTEM, 
                            USER_AND_LOCATION, PURCHASING, EXTENSION_ATTRIBUTES.
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mobile Device Group Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Mobile Device Profile Upload arguments:
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

Package Upload arguments:
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
    --jcds                  Deprecated, ignored 
    --jcds2                 Use jcds endpoint for package upload to JCDS 
    --aws                   Use AWS CDP for package upload. Requires aws-cli to be installed 
    --api                   Use v1/packages endpoint for package upload to cloud DP
    --recalculate           Recalculate packages if using --jcds2 or --api modes
    --md5                   Use MD5 hash instead of SHA512. Required for packages 
                            to be installable via MDM InstallEnterpriseApplication

Package Metadata Upload arguments:
    --name <string>         The package display name
    --pkg <path>            The package filename
    --priority <int>        The priority
    --category <string>     The category. Must exist.
    --info <string>         Pkg information field
    --notes <string>        Pkg notes field
    --reboot_required       Set the 'reboot required' option
    --os-requirement <string>
                            Set OS requirement for the pkg
    --required-processor <string>
                            Set CPU type requirement for the pkg
    --send-notification     Set to send a notification when the package is installed
    --replace               Set to replace the pkg metadata if no package is uploaded

Policy Upload arguments:
    --name <string>         The name
    --template <path>       XML template
    --icon <path>           Full path to an icon file for Self Service policies
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item
    --replace-icon          Set to replace the existing icon if it has the same name
    --retain-scope          Retain existing scope when updating an item

Patch Policy Upload arguments:
    --name <string>         The patch policy name
    --pkg <path>            Name of the package to uplaod
    --version <string>      The package (or app) version
    --title <string>        The patch software title
    --template <path>       XML template
    --policy <string>       Name of an existing policy containing the desired icon for the patch policy
    --key X=Y               Substitutable values in the template. Multiple values can be supplied
    --replace               Replace existing item

Script Upload arguments:
    --name <string>         The name
    --script <path>         Full path of the script to be uploaded
    --key X=Y               Substitutable values in the script. Multiple values can be supplied
    --parameter[4-11]
                            Script parameter labels 
    --skip-substitution
                            Skip substitution of variables in the script
    --replace               Replace existing item

Software Restriction Upload arguments:
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

READ OPTIONS

API Object Read arguments:
    --name <string>         The object name, if --all is not specified
    --all                   Read all objects
    --list                  Output a list all objects and nothing else
    --type <string>         The object type (e.g. policy)
    --settings-key          For settings-style endpoints, specify a key to get the value of
    --output <string>       Optional path to output the parsed XML to. Directories to path must exist.

DELETE OPTIONS

API Object Delete arguments:
    --name <string>         The object name
    --type <string>         The object type (e.g. policy)

Computer Group Delete arguments:
    --name <string>         The computer group name

Policy Delete arguments:
    --name <string>         The policy name

MISCELLANEOUS ACTIONS OPTIONS

Extension Attribute Popup Choice Adjuster arguments:
    --template <path>       XML template
    --operation <string>    The operation to perform, either 'add' or 'remove'
    --value <string>        The value to add or remove
    --not-strict            Don't fail if adding a choice value that already exists 
                            or removing a choice value that does not exist in the raw object
    --output <dir>          Optional directory to output the parsed XML to. Directory must exist.

Package Clean arguments:
    --name <string>         The name to match
    --smb-url <url>         URL of the fileshare distribution point (on premises Jamf Pro only)
    --smb-user <SMB_USERNAME>
                            Username with share access
    --smb_pass <SMB_PASSWORD>
                            Password of the user
    --dry-run               Dry run mode. No files will be deleted.

Unused Package Clean arguments:
    --smb-url <url>         URL of the fileshare distribution point (on premises Jamf Pro only)
    --smb-user <SMB_USERNAME>
                            Username with share access
    --smb_pass <SMB_PASSWORD>
                            Password of the user
    --output <dir>          Optional directory to output the list to a CSV. Directory must exist.
    --dry-run               Dry run mode. No files will be deleted.
    --slack-url <url>       The slack_webhook_url

Package Recalculate arguments: None

Policy Log Flush arguments:
    --name <string>         The policy name
    --interval              The log flush interval

Scope Adjust arguments:
    --template <path>       XML template
    --operation <string>    The operation to perform, either 'add' or 'remove'
    --scope-type <string>   The scope type, either 'target', 'limitation' or 'exclusion'
    --type <string>         The scopeable object type, either 'computer_group', 
                            'mobile_device_group', 'user_group'
    --name <string>         The name of the scopeable object
    --not-strict            Don't fail if adding a scopable object that already exists 
                            or removing a scopable object that does not exist in the raw object
    --not-stripped          Don't strip all XML tags except for general/id and scope
    --output <dir>          Optional directory to output the parsed XML to. Directory must exist.

NOTIFICATION OPTIONS

Jira notifications arguments:
    --name <string>         The name
    --policy-category <string>
                            The POLICY_CATEGORY
    --pkg-category <string> The PKG_CATEGORY
    --patch-name <string>   The patch policy name
    --pkg-name <string>     The package name
    --version <string>      The package (or app) version
    --patch-uploaded        Pretends that a patch was updated (sets a value to jamfpatchuploader_summary_result)
    --pkg-uploaded          Pretends that a package was uploaded (sets a value to jamfpackageuploader_summary_result)
    --policy-uploaded       Pretends that a policy was uploaded (sets a value to jamfpolicyuploader_summary_result)
    --jira-url <url>        The Jira URL
    --jira-user <string>    The Jira account username
    --jira-api-token <string>
                            The Jira API token
    --jira-project <string> The Jira Project ID
    --jira-issue-type <string>
                            The Jira Issue Type ID
    --jira-priority <string>
                            The Jira Issue Priority ID
    --icon <url>            The Slack icon URL

Slack notifications arguments:
    --name <string>         The name
    --policy-category <string>
                            The POLICY_CATEGORY
    --pkg-category <string> The PKG_CATEGORY
    --pkg-name <string>     The package name
    --version <string>      The package (or app) version
    --patch-uploaded        Pretends that a patch was updated (sets a value to jamfpatchuploader_summary_result)
    --pkg-uploaded          Pretends that a package was uploaded (sets a value to jamfpackageuploader_summary_result)
    --policy-uploaded       Pretends that a policy was uploaded (sets a value to jamfpolicyuploader_summary_result)
    --slack-url <url>       The slack_webhook_url
    --slack-user <string>   The Slack user to display
    --icon <url>            The Slack icon URL
    --channel <string>      The Slack channel to post to
    --emoji <string>        the Slack icon emoji

Teams notifications arguments:
    --name <string>         The name
    --policy-category <string>
                            The POLICY_CATEGORY
    --pkg-category <string> The PKG_CATEGORY
    --patch-name <string>   The patch policy name
    --pkg-name <string>     The package name
    --version <string>      The package (or app) version
    --patch-uploaded        Pretends that a patch was updated (sets a value to jamfpatchuploader_summary_result)
    --pkg-uploaded          Pretends that a package was uploaded (sets a value to jamfpackageuploader_summary_result)
    --policy-uploaded       Pretends that a policy was uploaded (sets a value to jamfpolicyuploader_summary_result)
    --teams-url <url>       The teams_webhook_url
    --teams-user <string>   The Teams user to display
    --icon <url>            The Slack icon URL

"
}

##############
## DEFAULTS ##
##############

temp_processor_plist="/tmp/jamf_upload/processor.plist"
temp_receipt="/tmp/jamf_upload/processor_receipt.plist"
mkdir -p "/tmp/jamf_upload"

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
elif [[ $object == "apirole" ]]; then 
    processor="JamfAPIRoleUploader"
elif [[ $object == "apiclient" ]]; then 
    processor="JamfAPIClientUploader"
elif [[ $object == "category" ]]; then 
    processor="JamfCategoryUploader"
elif [[ $object == "computerprestage" ]]; then 
    processor="JamfComputerPreStageUploader"
elif [[ $object == "delete" || $object == "objdelete" || $object == "objectdelete" ]]; then
    processor="JamfObjectDeleter"
elif [[ $object == "group" || $object == "computergroup" ]]; then
    processor="JamfComputerGroupUploader"
elif [[ $object == "groupdelete" || $object == "computergroupdelete" ]]; then
    processor="JamfComputerGroupDeleter"
elif [[ $object == "profile" || $object == "computerprofile" ]]; then
    processor="JamfComputerProfileUploader"
elif [[ $object == "dock" || $object == "dockitem" ]]; then
    processor="JamfDockItemUploader"
elif [[ $object == "ea" || $object == "extensionattribute" || $object == "computerextensionattribute" ]]; then
    processor="JamfExtensionAttributeUploader"
elif [[ $object == "eapopup" || $object == "eapopupadjuster" ]]; then
    processor="JamfExtensionAttributePopupChoiceAdjuster"
elif [[ $object == "icon" ]]; then
    processor="JamfIconUploader"
elif [[ $object == "macapp" ]]; then
    processor="JamfMacAppUploader"
elif [[ $object == "mobiledeviceapp" ]]; then
    processor="JamfMobileDeviceAppUploader"
elif [[ $object == "mobiledeviceea" || $object == "mobiledeviceextensionattribute" ]]; then
    processor="JamfMobileDeviceExtensionAttributeUploader"
elif [[ $object == "mobiledevicegroup" ]]; then
    processor="JamfMobileDeviceGroupUploader"
elif [[ $object == "mobiledeviceprofile" ]]; then
    processor="JamfMobileDeviceProfileUploader"
elif [[ $object == "msu" || $object == "managedsoftwareupdateplan" ]]; then
    processor="JamfMSUPlanUploader"
elif [[ $object == "obj"* || $object == "classicobj"* ]]; then
    processor="JamfObjectUploader"
elif [[ $object == "pkg" || $object == "package" ]]; then
    processor="JamfPackageUploader"
elif [[ $object == "pkgclean" ]]; then
    processor="JamfPackageCleaner"
elif [[ $object == "unusedpkgclean" ]]; then
    processor="JamfUnusedPackageCleaner"
elif [[ $object == "pkgdata" ]]; then
    processor="JamfPkgMetadataUploader"
elif [[ $object == "pkgcalc" || $object == "packagerecalculate" ]]; then
    processor="JamfPackageRecalculator"
elif [[ $object == "policy" ]]; then
    processor="JamfPolicyUploader"
elif [[ $object == "policydelete" ]]; then
    processor="JamfPolicyDeleter"
elif [[ $object == "policyflush" ]]; then
    processor="JamfPolicyLogFlusher"
elif [[ $object == "patch" ]]; then
    processor="JamfPatchUploader"
elif [[ $object == "read" ]]; then
    processor="JamfObjectReader"
elif [[ $object == "restriction" || $object == "softwarerestriction" ]]; then
    processor="JamfSoftwareRestrictionUploader"
elif [[ $object == "scope" ]]; then
    processor="JamfScopeAdjuster"
elif [[ $object == "script" ]]; then
    processor="JamfScriptUploader"
elif [[ $object == "jira" ]]; then
    processor="JamfUploaderJiraIssueCreator"
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
            elif [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_input_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_input_type='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfObjectReader" || $processor == "JamfObjectDeleter" || $processor == "JamfObjectUploader" ]]; then
                # override for generic items, as this key is written later, normally providing the value of $object
                object="$1"
            elif [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace scopeable_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote scopeable_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --domain)
            shift
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace domain -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote domain='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --group|--group_name|--group-name)
            shift
            if [[ $processor == "JamfAccountUploader" ]]; then
                if plutil -replace group -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote group='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMSUPlanUploader" ]]; then
                if plutil -replace group_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote group_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --priority) 
            shift
            if [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace category_priority -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote category_priority='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            elif [[ $processor == "JamfAPIRoleUploader" ]]; then
                if plutil -replace replace_api_role -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_api_role='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace replace_api_client -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_api_client='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace replace_category -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_category='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" || $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace replace_group -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_group='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerPreStageUploader" ]]; then
                if plutil -replace replace_prestage -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_prestage='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace replace_profile -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_profile='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace replace_dock_item -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_dock_item='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace replace_ea -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_ea='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace replace_macapp -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_macapp='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceAppUploader" ]]; then
                if plutil -replace replace_mobiledeviceapp -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_mobiledeviceapp='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfObjectUploader" ]]; then
                if plutil -replace replace_object -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote replace_object='True' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" ]]; then
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
            elif [[ $processor == "JamfAPIRoleUploader" ]]; then
                if plutil -replace api_role_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_role_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace api_client_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_client_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfCategoryUploader" ]]; then
                if plutil -replace category_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote category_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" || $processor == "JamfComputerGroupDeleter" ]]; then
                if plutil -replace computergroup_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote computergroup_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerPreStageUploader" ]]; then
                if plutil -replace prestage_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote prestage_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfDockItemUploader" ]]; then
                if plutil -replace dock_item_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote dock_item_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace macapp_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote macapp_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceAppUploader" ]]; then
                if plutil -replace mobiledeviceapp_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledeviceapp_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace mobiledevicegroup_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledevicegroup_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfObjectReader" || $processor == "JamfObjectDeleter" || $processor == "JamfObjectUploader" ]]; then
                if plutil -replace object_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            elif [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace scopeable_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote scopeable_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace script_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_name='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
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
            elif [[ $processor == "JamfAPIRoleUploader" ]]; then
                if plutil -replace api_role_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_role_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerGroupUploader" ]]; then
                if plutil -replace computergroup_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote computergroup_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerPreStageUploader" ]]; then
                if plutil -replace prestage_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote prestage_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfComputerProfileUploader" || $processor == "JamfMobileDeviceProfileUploader" ]]; then
                if plutil -replace profile_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote profile_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfExtensionAttributePopupChoiceAdjuster" ]]; then
                if plutil -replace object_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMacAppUploader" ]]; then
                if plutil -replace macapp_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote macapp_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceAppUploader" ]]; then
                if plutil -replace mobiledeviceapp_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledeviceapp_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfMobileDeviceGroupUploader" ]]; then
                if plutil -replace mobiledevicegroup_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote mobiledevicegroup_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfObjectUploader" ]]; then
                if plutil -replace object_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPatchUploader" ]]; then
                if plutil -replace patch_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote patch_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPolicyUploader" ]]; then
                if plutil -replace policy_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote policy_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace object_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_template='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfSoftwareRestrictionUploader" ]]; then
                if plutil -replace restriction_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote restriction_template='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --api-client-id)
            shift
            if [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace api_client_id -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_client_id='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --api-role-name)
            shift
            if [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace api_role_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_role_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --enabled)
            if [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace api_client_enabled -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote api_client_enabled='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --lifetime|--access-token-lifetime)
            shift
            if [[ $processor == "JamfAPIClientUploader" ]]; then
                if plutil -replace access_token_lifetime -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote access_token_lifetime='$1' into $temp_processor_plist"
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
            elif [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            elif [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_description -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_description='$1' into $temp_processor_plist"
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
            elif [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if plutil -replace ea_script_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_script_path='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --not-strict) 
            if [[ $processor == "JamfExtensionAttributePopupChoiceAdjuster" || $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace strict_mode -string "False" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote strict_mode='False' into $temp_processor_plist"
                fi
            fi
            ;;
        --operation)
            shift
            if [[ $processor == "JamfExtensionAttributePopupChoiceAdjuster" ]]; then
                if plutil -replace choice_operation -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote choice_operation='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace scoping_operation -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote scoping_operation='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --output)
            shift
            if [[ $processor == "JamfExtensionAttributePopupChoiceAdjuster" || $processor == "JamfObjectReader" || $processor == "JamfUnusedPackageCleaner" || $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace output_dir -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote output_dir='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --value)
            shift
            if [[ $processor == "JamfExtensionAttributePopupChoiceAdjuster" ]]; then
                if plutil -replace choice_value -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote choice_value='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --disabled)
            if [[ $processor == "JamfExtensionAttributeUploader" ]]; then
                if plutil -replace ea_enabled -string "False" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_enabled='False' into $temp_processor_plist"
                fi
            fi
            ;;
        --data-type)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_data_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_data_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --inventory-display)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_inventory_display -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_inventory_display='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --ldap-mapping)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_directory_service_attribute_mapping -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_directory_service_attribute_mapping='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --choices)
            shift
            if [[ $processor == "JamfExtensionAttributeUploader" || $processor == "JamfMobileDeviceExtensionAttributeUploader" ]]; then
                if plutil -replace ea_popup_choices -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote ea_popup_choices='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --script|--script-path)
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
            if [[ $processor == "JamfMacAppUploader" || $processor == "JamfMobileDeviceAppUploader" ]]; then
                if plutil -replace clone_from -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote clone_from='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --appconfig)
            shift
            if [[ $processor == "JamfMobileDeviceAppUploader" ]]; then
                if plutil -replace appconfig_template -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote appconfig_template='$1' into $temp_processor_plist"
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
        --days*)
            shift
            if [[ $processor == "JamfMSUPlanUploader" ]]; then
                if plutil -replace days_until_force_install -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote days_until_force_install='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --device-type)
            shift
            if [[ $processor == "JamfMSUPlanUploader" ]]; then
                if plutil -replace device_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote device_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --version) 
            shift
            if [[ $processor == "JamfMSUPlanUploader" || $processor == "JamfPatchUploader" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace version -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote version='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --all) 
            if [[ $processor == "JamfObjectReader" ]]; then
                if plutil -replace all_objects -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote all_objects='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --id)
            shift
            if [[ $processor == "JamfObjectReader" || $processor == "JamfObjectUploader" ]]; then
                if plutil -replace object_id -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote object_id='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --list) 
            if [[ $processor == "JamfObjectReader" ]]; then
                if plutil -replace list_only -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote list_only='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --settings-key) 
            shift
            if [[ $processor == "JamfObjectReader" ]]; then
                if plutil -replace settings_key -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote settings_key='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --dry-run) 
            if [[ $processor == "JamfPackageCleaner" || $processor == "JamfUnusedPackageCleaner" ]]; then
                if plutil -replace dry_run -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote dry_run='True' into $temp_processor_plist"
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
        --smb_url|--smb-url)
            shift
            if [[ $processor == "JamfPackageCleaner" || $processor == "JamfUnusedPackageCleaner" || $processor == "JamfPackageUploader" ]]; then
                if plutil -replace SMB_URL -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_URL='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_user*|--smb-user*)  
            ## allows --smb_user, --smb_username, --smb-user, --smb-username
            shift
            if [[ $processor == "JamfPackageCleaner" || $processor == "JamfUnusedPackageCleaner" || $processor == "JamfPackageUploader" ]]; then
                if plutil -replace SMB_USERNAME -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_USERNAME='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --smb_pass*|--smb-pass*)  
            ## allows --smb_pass, --smb_password, --smb-pass, --smb-password
            shift
            if [[ $processor == "JamfPackageCleaner" || $processor == "JamfUnusedPackageCleaner" || $processor == "JamfPackageUploader" ]]; then
                if plutil -replace SMB_PASSWORD -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote SMB_PASSWORD='[redacted]' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg|--pkg_path|--pkg-path)
            shift
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace pkg_path -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_path='$1' into $temp_processor_plist"
                fi
            elif [[ $processor == "JamfPkgMetadataUploader" ]]; then
                if plutil -replace pkg_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-name|--pkg_name) 
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" || $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" || $processor == "JamfPatchUploader" ]]; then
                if plutil -replace pkg_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_name='$1' into $temp_processor_plist"
                fi
            fi
           ;;
        --info)
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
                if plutil -replace reboot_required -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote reboot_required='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --os_requirement*|--os-requirement*|--osrequirement*)  
            ## allows --os_requirement, --os-requirement, --osrequirements
            shift
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
                if plutil -replace required_processor -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote required_processor='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --send_notification|--send-notification) 
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
            if [[ $processor == "JamfPackageUploader" || $processor == "JamfPkgMetadataUploader" ]]; then
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
        --aws) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace aws_cdp_mode -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote aws_cdp_mode='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --api) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace pkg_api_mode -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote pkg_api_mode='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --recalculate) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace recalculate -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote recalculate='True' into $temp_processor_plist"
                fi
            fi
            ;;
        --md5) 
            if [[ $processor == "JamfPackageUploader" ]]; then
                if plutil -replace md5 -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote md5='True' into $temp_processor_plist"
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
            elif [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace policy_name -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote policy_name='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --version) 
            shift
            if [[ $processor == "JamfPatchUploader" || $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
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
        --not-stripped) 
            if [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace strip_raw_xml -string "False" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote strip_raw_xml='False' into $temp_processor_plist"
                fi
            fi
            ;;
        --scope-type)
            shift
            if [[ $processor == "JamfScopeAdjuster" ]]; then
                if plutil -replace scoping_type -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote scoping_type='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        "--script_parameter"*|"--script-parameter"*|"--parameter"*|--p4|--p5|--p6|--p7|--p8|--p9|--p10|--p11)
            param_number="${1: -1}"
            if [[ ! $param_number ]]; then
                exit 1
            fi
            shift
            if [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace "script_parameter$param_number" -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote script_parameter$param_number='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --skip-substitution) 
            if [[ $processor == "JamfScriptUploader" ]]; then
                if plutil -replace skip_script_key_substitution -string "True" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote skip_script_key_substitution='True' into $temp_processor_plist"
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
        --slack-url) 
            shift
            if [[ $processor == "JamfUnusedPackageCleaner" || $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_webhook_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_webhook_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-issue)
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_issue_id -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_issue_id='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-api-token) 
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_api_token -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_api_token='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-project) 
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_project_id -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_project_id='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-priority) 
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_priority_id -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_priority_id='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-url)
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_url -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_url='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --jira-user*) 
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" ]]; then
                if plutil -replace jira_username -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jira_username='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-category)
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace PKG_CATEGORY -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote PKG_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-category)
            shift
            if [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace POLICY_CATEGORY -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote POLICY_CATEGORY='$1' into $temp_processor_plist"
                fi
            fi
            ;;
        --patch-uploaded) 
            if [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpatchuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpatchuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --pkg-uploaded) 
            if [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpackageuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpackageuploader_summary_result='true' into $temp_processor_plist"
                fi
            fi
            ;;
        --policy-uploaded) 
            if [[ $processor == "JamfUploaderJiraIssueCreator" || $processor == "JamfUploaderSlacker" || $processor == "JamfUploaderTeamsNotifier" ]]; then
                if plutil -replace jamfpolicyuploader_summary_result -string "true" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote jamfpolicyuploader_summary_result='true' into $temp_processor_plist"
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
        --slack-user) 
            shift
            if [[ $processor == "JamfUploaderSlacker" ]]; then
                if plutil -replace slack_username -string "$1" "$temp_processor_plist"; then
                    echo "   [jamf-upload] Wrote slack_username='$1' into $temp_processor_plist"
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

# add the object type for items using the generic JamfObjectReader and JamfObjectUploader processors
if [[ $processor == "JamfObjectReader" || $processor == "JamfObjectDeleter" || $processor == "JamfObjectUploader" ]]; then
    if plutil -replace object_type -string "$object" "$temp_processor_plist"; then
        echo "   [jamf-upload] Wrote object_type='$object' into $temp_processor_plist"
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
