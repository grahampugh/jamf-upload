#!/bin/bash

:<<DOC
A wrapper script for running the jamf-api-tool script
DOC

###########
## USAGE ##
###########

usage() {
    echo "
Usage: 
./jamf-api-tool.sh [--help] [arguments]

This script currently only handles package deletion. More to follow.

Arguments:
    --prefs <path>          Inherit AutoPkg prefs file provided by the full path to the file
    -v[vvv]                 Set value of verbosity
    --url <JSS_URL>         The Jamf Pro URL
    --user <API_USERNAME>   The API username
    --pass <API_PASSWORD>   The API user's password

"
}

##############
## DEFAULTS ##
##############

# this folder
DIR=$(dirname "$0")
tool_directory="$DIR/standalone_uploaders"
tool="jamf_api_tool.py"
tmp_prefs="${HOME}/Library/Preferences/jamf-api-tool.plist"
autopkg_prefs="${HOME}/Library/Preferences/com.github.autopkg.plist"

###############
## ARGUMENTS ##
###############

args=()

# select object
object="package"
args+=("--$object")

# select actions
args+=("--unused")
args+=("--delete")


while test $# -gt 0 ; do
    case "$1" in
        --prefs)
            shift
            autopkg_prefs="$1"
            ;;
        -v*)
            args+=("$1")
            ;;
        --url) 
            shift
            url="$1"
            ;;
        --user*)  
            ## allows --user or --username
            shift
            user="$1"
            ;;
        --pass*)  
            ## allows --pass or --password
            shift
            password="$1"
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

if [ "$url" ] && [ "$user" ] && [ "$password" ]; then
    # write temp prefs file
    /usr/bin/defaults write "$tmp_prefs" JSS_URL "$url"
    /usr/bin/defaults write "$tmp_prefs" API_USERNAME "$user"
    /usr/bin/defaults write "$tmp_prefs" API_PASSWORD "$password"
    args+=("--prefs")
    args+=("$tmp_prefs")
elif [[ -f "$autopkg_prefs" ]]; then
    args+=("--prefs")
    args+=("$autopkg_prefs")
else
    echo "No credentials supplied"
    exit 1
fi

###############
## MAIN BODY ##
###############

# Ensure PYHTONPATH includes the AutoPkg libraries
if [[ -d "/Library/AutoPkg" ]]; then
    export PYTHONPATH="/Library/AutoPkg"
else
    echo "ERROR: AutoPkg is not installed"
    exit 1
fi

echo 
# Run the script and output to stdout
/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 "$tool_directory/$tool" "${args[@]}" 
