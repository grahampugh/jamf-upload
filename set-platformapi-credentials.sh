#!/bin/bash

# --------------------------------------------------------------------------------
# Script to add the required credentials into your login keychain to allow repeated use.
# This script can only operate on one tenant at a time, since each API client is unique.
# 1. Ask for the region
# 2. Ask for the API client ID 
# 3. Ask for the API client password
# 4. Check the credentials are working using the API
# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------------------------------

usage() {
    cat <<'USAGE'
Usage:
./set-platformapi-credentials.sh                  - set the Keychain Credentials

Options:
[no arguments]                                    - interactive mode
-r | --region (eu|us|apac)                        - region that the tenant is hosted in
--id | --client-id CLIENT_ID                      - use the specified client ID
--secret | --client-secret CLIENT_SECRET          - use the specified client secret
-v[vvv]                                           - Set value of verbosity (default is -v)

USAGE
}

get_region_url() {
        case $chosen_region in
        us)
            api_base_url="https://us.apigw.jamf.com"
            ;;
        eu)
            api_base_url="https://eu.apigw.jamf.com"
            ;;
        apac)
            api_base_url="https://apac.apigw.jamf.com"
            ;;
        *)
            echo "ERROR: Invalid region specified. Please use one of: us, eu, apac."
            exit 1
            ;;
    esac
    if [[ $verbose -gt 0 ]]; then
        echo "   [get_region_url] API Base URL: $api_base_url"
    fi
}

verify_credentials() {
    echo "Verifying credentials for $api_base_url"

    # check for username entry in login keychain
    # jss_api_user=$("${this_script_dir}/keychain.sh" -t internet -u -s "$jss_url")
    client_id=$(/usr/bin/security find-internet-password -s "$api_base_url" -g 2>/dev/null | /usr/bin/grep "acct" | /usr/bin/cut -d \" -f 4 )

    if [[ ! $client_id ]]; then
        echo "No keychain entry for $api_base_url found. Please run the set-credentials.sh script to add the Client ID to your keychain"
        exit 1
    fi

    # check for password entry in login keychain
    # jss_api_password=$("${this_script_dir}/keychain.sh" -t internet -p -s "$jss_url")
    client_secret=$(/usr/bin/security find-internet-password -s "$api_base_url" -a "$client_id" -w -g 2>&1 )

    if [[ ! $client_secret ]]; then
        echo "No password/Client Secret for $client_id found. Please run the set-credentials.sh script to add the Client Secret to your keychain"
        exit 1
    fi

    # get a bearer token
    output_location="/tmp/jamf_pro_credentials_verification"
    mkdir -p "$output_location"
    output_file_token="$output_location/output_token.txt"

    if ! http_response=$(curl \
        --silent \
        --show-error \
        --request POST \
        "$api_base_url/auth/token" \
        --header 'Content-Type: application/x-www-form-urlencoded' \
        --header 'Accept: application/json' \
    	--data-urlencode 'grant_type=client_credentials' \
    	--data-urlencode "client_id=$client_id" \
        --data-urlencode "client_secret=$client_secret" \
        --write-out "%{http_code}" \
        --output "$output_file_token"); then
        echo "ERROR: Failed to connect to the Platform API."
        return 1
    fi

    echo "Token request HTTP response: $http_response"
    if [[ $http_response -lt 400 ]]; then
        token=$(plutil -extract access_token raw "$output_file_token")
        if [[ $token ]]; then
            echo "Token successfully retrieved"
            return 0
        else
            echo "Token download failed - no token received"
            return 1
        fi
    else
        echo "Token download failed - check authentication details"
        exit 1
    fi
}


# --------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------

while test $# -gt 0 ; do
    case "$1" in
        -r|--region)
            shift
            chosen_region="$1"
            ;;
        --user|--id|--client-id)
            shift
            chosen_id="$1"
            ;;
        --pass|--secret|--client-secret)
            shift
            chosen_secret="$1"
            ;;
        -v*)
            verbose=1
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

cat << 'EOF'
Welcome to the Set Platform API Credentials tool!

(Please submit better names for this script as a GitHub Issue...)

This tool adds supplied credentials to your Login Keychain. 
Please note that if you have multiple entries in your Keychain for the same URL
with different usernames, this tool will remove them and replace them with the new credentials.
EOF

# set the URL based on the chosen region
if [[ $chosen_region ]]; then
    get_region_url
else
    # ask for the region
    echo "Enter region (eu, us, apac) for the tenant hosted on $chosen_instance"
    read -r -p "Region : " chosen_region
    if [[ ! $chosen_region ]]; then
        echo "   [main] No region supplied"
        exit 1
    fi
    get_region_url
    if [[ ! $api_base_url ]]; then
        echo "   [main] ERROR: Could not determine API URL for region $chosen_region"
        exit
    fi
fi

# Ask for the username (show any existing value of first instance in list as default)
if [[ ! $chosen_id ]]; then
    echo "Enter Client ID for $api_base_url"
    read -r -p "Client ID : " chosen_id
    if [[ ! $chosen_id ]]; then
        echo "   [main] No Client ID supplied"
        exit 1
    fi
fi

# check for existing service entry in login keychain
region_base="${api_base_url/*:\/\//}"

# first check if there is an entry for the server
server_check=$(security find-internet-password -s "$api_base_url" 2>/dev/null)
if [[ $server_check ]]; then
    echo "Keychain entry/ies for $region_base found"
    # next check if there is an entry for the user on that server
    kc_check=$(security find-internet-password -s "$api_base_url" -l "$region_base ($chosen_id)" -a "$chosen_id" -g 2>/dev/null)

    if [[ $kc_check ]]; then
        echo "Keychain entry for $chosen_id found on $region_base"
        # check for existing password entry in login keychain
        client_secret=$(security find-internet-password -s "$api_base_url" -l "$region_base ($chosen_id)" -a "$chosen_id" -w -g 2>&1)
        if [[ ${#client_secret} -gt 0 && $client_secret != "security: "* ]]; then
            echo "Password/Client Secret for $chosen_id found on $region_base"
        else
            echo "Password/Client Secret for $chosen_id not found on $region_base"
            client_secret=""
        fi
    else
        echo "Keychain entry for $chosen_id not found on $region_base"
    fi
else
    echo "Keychain entry for $region_base not found"
fi

# now delete all existing entries from the selected instance for any username
# Find and delete all keychain entries for this region, repeatedly until none remain
deleted_count=0
while true; do
    # Find the first entry for this region
    entry=$(security find-internet-password -s "$api_base_url" 2>/dev/null)
    if [[ -z "$entry" ]]; then
        echo "No more entries found, done with $api_base_url"
        break
    fi
    
    # Extract the label from the entry (stored in 0x00000007 attribute)
    label=$(echo "$entry" | grep "0x00000007" | awk -F'"' '{print $2}')
    if [[ $label == "$region_base ("*")" ]]; then
        # Delete this specific entry
        echo "Deleting password for $label"
        if security delete-internet-password -s "$api_base_url" -l "$label"; then
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
    echo "Deleted $deleted_count existing keychain entries for $region_base"
else
    echo "No existing keychain entries found for $region_base"
fi

echo

if [[ ! "$chosen_secret" ]]; then
    echo "Enter Client Secret for $chosen_id on $region_base"
    [[ $instance_pass ]] && echo "(or press ENTER to use existing Client Secret from keychain for $chosen_id)"
    read -r -s -p "Pass : " chosen_secret
    if [[ $instance_pass && ! "$chosen_secret" ]]; then
        chosen_secret="$instance_pass"
    elif [[ ! $chosen_secret ]]; then
        echo "No Client Secret supplied"
        exit 1
    fi
fi

# Apply to selected instance
echo
echo
security add-internet-password -U -s "$api_base_url" -l "$region_base ($chosen_id)" -a "$chosen_id" -w "$chosen_secret"
echo "   [main] Credentials for $api_base_url (user $chosen_id) added to keychain"

# Verify the credentials
echo
echo "   [main] Checking credentials for $api_base_url (user $chosen_id)"
if verify_credentials; then
    echo "   [main] Credentials for $api_base_url (user $chosen_id) verified"
else
    echo "   [main] ERROR: Credentials for $api_base_url (user $chosen_id) could not be verified"
fi

echo
echo "Script complete"
echo
