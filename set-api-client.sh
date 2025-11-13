#!/bin/bash

# --------------------------------------------------------------------------------
# Script to create an API role and client using Jamf Pro credentials which has the correct permissions required to perform all AutoPkg-related tasks. This is designed to ensure that the keychain stores only the API client ID and secret, and not Jamf Pro admin credentials.

# 1. Ask for the instance URL if not supplied as an argument
# 2. Check for an existing keychain entry for API role
# 3. If so, check if the credentials are working using the API
# 4. If so, offer to rotate the client secret
# 5. If not, ask for Jamf Pro admin credentials
# 6. Ask for the username
# 7. Ask for the password
# 8. If no Keychain entry for API role, rotate the client secret for the API client (or create a new API role and client if none exists)
# 9. Store the client ID and client secret in the Keychain
# 10. Check the credentials are working using the API
# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------------------------------

usage() {
    cat <<'USAGE'
Usage:
./set-api-client.sh                               - set the Keychain Credentials

Options:
[no arguments]                                    - interactive mode
-i JSS_URL                                        - perform action on a single instance
--user USERNAME             - use the specified client ID or username
--password PASSWORD         - use the specified client secret or password
--role ROLE_NAME            - use the specified API Role name (default: AutoPkg)
--client CLIENT_NAME        - use the specified API Client name (default: AutoPkg)
--overwrite                - overwrite existing valid credentials without prompting
-v[vvv]                                   - Set value of verbosity (default is -v)
USAGE
}

verify_credentials() {
    echo "Verifying credentials for $chosen_instance"

    # get a bearer token
    output_location="/tmp/jamf_pro_credentials_verification"
    mkdir -p "$output_location"
    output_file_token="$output_location/output_token.txt"

    http_response=$(
        curl --request POST \
        --silent \
        --url "$chosen_instance/api/v1/oauth/token" \
        --header 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode "client_id=$chosen_id" \
        --data-urlencode "grant_type=client_credentials" \
        --data-urlencode "client_secret=$chosen_secret" \
        --write-out "%{http_code}" \
        --header 'Accept: application/json' \
        --output "$output_file_token"
    )
    echo "Token request HTTP response: $http_response"
    if [[ $http_response -lt 400 && $http_response -ge 200 && -f "$output_file_token" ]]; then
        token=$(plutil -extract access_token raw "$output_file_token")
        echo "Token downloaded: $token"
    else
        echo "Token download failed"
        return 1
    fi
    return 0
}

create_or_update_api_role_and_client() {
    echo "Creating or updating API Role and Client function called"
    # Run AutoPkg recipe to create or update the API role and client
    autopkg run "$verbose" \
        --search-dir="$(dirname "$0")/Recipes" \
        --search-dir="$(dirname "$0")/../jamf-upload" \
        com.github.grahampugh.recipes.jamf.APIRoleClient-AutoPkg \
        --report-plist="$autopkg_report" \
        --key API_ROLE_NAME="$role_name" \
        --key API_CLIENT_NAME="$client_name" \
        --key JSS_URL="$chosen_instance" \
        --key API_USERNAME="$user" \
        --key API_PASSWORD="$password"
}

        # --search-dir="$HOME/Library/AutoPkg/RecipeRepos/com.github.grahampugh.jamf-upload" \
        # --search-dir="$HOME/Library/AutoPkg/RecipeRepos/com.github.autopkg.grahampugh-recipes" \


# --------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------

# Default values
autopkg_report="/tmp/jamf_pro_credentials_verification/recipe_report.plist"
role_name="AutoPkg"
client_name="AutoPkg"
overwrite=0
verbose="-v"

# get arguments
while test $# -gt 0 ; do
    case "$1" in
        -i|--instance)
            shift
            chosen_instance="$1"
            ;;
        --role)
            shift
            role_name="$1"
            ;;
        --client)
            shift
            client_name="$1"
            ;;
        --user)
            shift
            user="$1"
            ;;
        --pass)
            shift
            password="$1"
            ;;
        --overwrite)
            overwrite=1
            ;;
        -v*)
            verbose="$1"
            ;;
        *)
            echo
            usage
            exit 0
            ;;
    esac
    shift
done
echo

# start interactive prompt
cat << 'EOF'
Welcome to the Set API Client tool!

(Please submit better names for this script as a GitHub Issue...)

This tool adds supplied credentials to your Login Keychain. 
Please note that if you have multiple entries in your Keychain for the same URL
with different usernames, this tool will remove them and replace them with the new credentials.
EOF

# Ask for the instance URL if not supplied as an argument
if [[ ! $chosen_instance ]]; then
    echo "Enter Jamf Pro URL"
    read -r -p "URL : " chosen_instance
    if [[ ! $chosen_instance ]]; then
        echo "No instance supplied"
        exit 1
    fi
fi

if [[ "$chosen_instance" != *"."* ]]; then
    chosen_instance="$chosen_instance.jamfcloud.com"
fi
if [[ "$chosen_instance" != "https://"* ]]; then
    chosen_instance="https://$chosen_instance"
fi

instance_base="${chosen_instance/*:\/\//}"

# Check for an existing keychain entry for API clients on this instance
server_check=$(security find-internet-password -s "$chosen_instance" 2>/dev/null)
if [[ $server_check ]]; then
    echo "Keychain entry/ies for $instance_base found"
    # next check if there is an entry for the user on that server
    kc_check=$(security find-internet-password -s "$chosen_instance" -l "$instance_base ($client_name)" -g 2>/dev/null)

    if [[ $kc_check ]]; then
        echo "Keychain entry for $client_name found on $instance_base"
        # get account name
        chosen_id=$(security find-internet-password -s "$chosen_instance" -l "$instance_base ($client_name)" 2>/dev/null | grep "acct" | cut -d \" -f 4)
        echo "Client ID: $chosen_id"

        # check for existing password entry in login keychain
        chosen_secret=$(security find-internet-password -s "$chosen_instance" -l "$instance_base ($client_name)" -a "$chosen_id" -w -g 2>&1)
        if [[ ${#chosen_secret} -gt 0 && $chosen_secret != "security: "* ]]; then
            echo "Client Secret for $client_name found on $instance_base"

            # Check if the credentials are working using the API
            verify_credentials "$chosen_instance"
            if [[ $? -eq 0 ]]; then
                if [[ ! $overwrite ]]; then
                    echo
                    read -r -p "Existing credentials are valid. Do you want to rotate the Client Secret? (y/N) : " rotate_choice
                    if [[ ! $rotate_choice =~ ^[Yy]$ ]]; then
                        echo "Exiting without changes."
                        exit 0
                    fi
                fi
                echo "Existing credentials are valid but user has chosen to rotate the Client Secret."
            else
                echo "Existing credentials are invalid. They will be replaced."
            fi

        else
            echo "Client Secret for $client_name not found on $instance_base"
            instance_pass=""
        fi
    else
        echo "Keychain entry for $client_name not found on $instance_base"
    fi
else
    echo "Keychain entry for $instance_base not found"
fi


# Ask for the username (show any existing value of first instance in list as default)
if [[ ! $user ]]; then
    echo "Enter username for $chosen_instance"
    read -r -p "Username : " user
    if [[ ! $user ]]; then
        echo "No username supplied"
        exit 1
    fi
fi

if [[ ! "$password" ]]; then
    echo "Enter password for $user on $instance_base"
    read -r -s -p "Pass : " password
    if [[ ! "$password" ]]; then
        echo "No password supplied"
        exit 1
    fi
fi

# Create/updatre the API role and create/rotate the API client 
echo
echo "Creating or updating API Role '$role_name' and Client '$client_name' on $instance_base ..."
# Call the function to create or update the API role and client
create_or_update_api_role_and_client 
if [[ $? -ne 0 ]]; then
    echo "Failed to create or update API role/client. Exiting."
    exit 1
fi

echo "API Role and Client created or updated successfully."

# print out the client ID and secret for debugging
chosen_id=$(plutil -extract "summary_results.jamfapiclientuploader_summary_result.data_rows.0.api_client_id" raw "$autopkg_report")
chosen_secret=$(plutil -extract "summary_results.jamfapiclientuploader_summary_result.data_rows.0.api_client_secret" raw "$autopkg_report")

# now delete the report for security purposes
rm -f "$autopkg_report"

# stop if no client ID or secret found
if [[ ! $chosen_id || ! $chosen_secret ]]; then
    echo "No Client ID or Secret found in AutoPkg report. Exiting."
    exit 1
fi

echo
# Find and delete all keychain entries for this instance_base, repeatedly until none remain
deleted_count=0
while true; do
    # Find the first entry for this instance
    entry=$(security find-internet-password -s "$chosen_instance" 2>/dev/null)
    if [[ -z "$entry" ]]; then
        echo "No more entries found, done with $chosen_instance"
        break
    fi
    
    # Extract the label from the entry (stored in 0x00000007 attribute)
    label=$(echo "$entry" | grep "0x00000007" | awk -F'"' '{print $2}')
    if [[ $label == "$instance_base ("*")" ]]; then
        # Delete this specific entry
        echo "Deleting password for $label"
        if security delete-internet-password -s "$chosen_instance" -l "$label"; then
            ((deleted_count++))
        else
            # If deletion failed, break to avoid infinite loop
            break
        fi
    else
        # No matching label pattern found, break the loop
        break
    fi
done

if [[ $deleted_count -gt 0 ]]; then
    echo "Deleted $deleted_count existing keychain entries for $instance_base"
else
    echo "No existing keychain entries found for $instance_base"
fi

echo

# add new credentials to keychain
echo
echo
security add-internet-password -U -s "$chosen_instance" -l "$instance_base ($client_name)" -a "$chosen_id" -w "$chosen_secret"
echo "Credentials for $instance_base ($client_name) added to keychain"

# Verify the credentials

echo
echo "Verifying credentials for $instance_base ($client_name)..."
verify_credentials "$chosen_instance"
if [[ $? -eq 0 ]]; then
    echo "Credentials verified successfully."
else
    echo "Failed to verify credentials."
    exit 1
fi

echo
echo "Script complete"
echo
