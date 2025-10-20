#!/bin/bash

# --------------------------------------------------------------------------------
# Script to add the required credentials into your login keychain to allow repeated use.

# 1. Ask for the instance URL
# 2. Ask for the username (show any existing value of first instance in list as default)
# 3. Ask for the password (show the associated user if already existing)
# 4. Loop through each selected instance, check for an existing keychain entry, create or overwrite
# 5. Check the credentials are working using the API
# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------------------------------

usage() {
    cat <<'USAGE'
Usage:
./set_platformapi_credentials.sh                  - set the Keychain Credentials

Options:
[no arguments]                                    - interactive mode
-i JSS_URL                                        - perform action on a single instance
--user | --id | --client-id CLIENT_ID             - use the specified client ID or username
--pass | --secret | --client-secret CLIENT_SECRET - use the specified client secret or password
-v[vvv]                                   - Set value of verbosity (default is -v)
USAGE
}

verify_credentials() {
    local jss_url="$1"
    echo "Verifying credentials for $jss_url"

    # check for username entry in login keychain
    # jss_api_user=$("${this_script_dir}/keychain.sh" -t internet -u -s "$jss_url")
    jss_api_user=$(/usr/bin/security find-internet-password -s "$jss_url" -g 2>/dev/null | /usr/bin/grep "acct" | /usr/bin/cut -d \" -f 4 )

    if [[ ! $jss_api_user ]]; then
        echo "No keychain entry for $jss_url found. Please re-run this script and supply the user/Client ID to add to your keychain"
        exit 1
    fi

    # check for password entry in login keychain
    # jss_api_password=$("${this_script_dir}/keychain.sh" -t internet -p -s "$jss_url")
    jss_api_password=$(/usr/bin/security find-internet-password -s "$jss_url" -a "$jss_api_user" -w -g 2>&1 )

    if [[ ! $jss_api_password ]]; then
        echo "No password/Client Secret for $jss_api_user found. Please run the set-credentials.sh script to add the password/Client Secret to your keychain"
        exit 1
    fi

    # echo "$jss_api_user:$jss_api_password"  # UNCOMMENT-TO-DEBUG

    # get a bearer token
    output_location="/tmp/jamf_pro_credentials_verification"
    mkdir -p "$output_location"
    output_file_token="$output_location/output_token.txt"
    output_file_record="$output_location/output_record.txt"

    # check if the user is a UUID (therefore implying a Client ID)
    if [[ $jss_api_user =~ ^\{?[A-F0-9a-f]{8}-[A-F0-9a-f]{4}-[A-F0-9a-f]{4}-[A-F0-9a-f]{4}-[A-F0-9a-f]{12}\}?$ ]]; then
        http_response=$(
            curl --request POST \
            --silent \
            --url "$jss_url/api/oauth/token" \
            --header 'Content-Type: application/x-www-form-urlencoded' \
            --data-urlencode "client_id=$jss_api_user" \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_secret=$jss_api_password" \
            --write-out "%{http_code}" \
            --header 'Accept: application/json' \
            --output "$output_file_token"
        )
        echo "Token request HTTP response: $http_response"
        if [[ $http_response -lt 400 ]]; then
            token=$(plutil -extract access_token raw "$output_file_token")
        else
            echo "Token download failed"
            exit 1
        fi
    else
        http_response=$(
            curl --request POST \
            --silent \
            --url "$jss_url/api/v1/auth/token" \
            --user "$jss_api_user:$jss_api_password" \
            --write-out "%{http_code}" \
            --header 'Accept: application/json' \
            --output "$output_file_token"
        )
        echo "Token request HTTP response: $http_response"
        if [[ $http_response -lt 400 ]]; then
            token=$(plutil -extract token raw "$output_file_token")
        else
            echo "Token download failed"
            exit 1
        fi
    fi


    # check Jamf Pro version
    http_response=$(
        curl --request GET \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            "$jss_url/api/v1/jamf-pro-version" \
            --write-out "%{http_code}" \
            --output "$output_file_record"
    )
    echo "Version request HTTP response: $http_response"
}

echo

# --------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------

while test $# -gt 0 ; do
    case "$1" in
        -i|--instance)
            shift
            chosen_instance="$1"
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
Welcome to the Set Credentials tool!

(Please submit better names for this script as a GitHub Issue...)

This tool adds supplied credentials to your Login Keychain. 
Please note that if you have multiple entries in your Keychain for the same URL
with different usernames, this tool will remove them and replace them with the new credentials.
EOF

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

# Ask for the username (show any existing value of first instance in list as default)
if [[ ! $chosen_id ]]; then
    echo "Enter username or Client ID for $chosen_instance"
    read -r -p "User/Client ID : " chosen_id
    if [[ ! $chosen_id ]]; then
        echo "No username/Client ID supplied"
        exit 1
    fi
fi

# first check if there is an entry for the server
server_check=$(security find-internet-password -s "$chosen_instance" 2>/dev/null)
if [[ $server_check ]]; then
    echo "Keychain entry/ies for $instance_base found"
    # next check if there is an entry for the user on that server
    kc_check=$(security find-internet-password -s "$chosen_instance" -l "$instance_base ($chosen_id)" -a "$chosen_id" -g 2>/dev/null)

    if [[ $kc_check ]]; then
        echo "Keychain entry for $chosen_id found on $instance_base"
        # check for existing password entry in login keychain
        instance_pass=$(security find-internet-password -s "$chosen_instance" -l "$instance_base ($chosen_id)" -a "$chosen_id" -w -g 2>&1)
        if [[ ${#instance_pass} -gt 0 && $instance_pass != "security: "* ]]; then
            echo "Password/Client Secret for $chosen_id found on $instance_base"
        else
            echo "Password/Client Secret for $chosen_id not found on $instance_base"
            instance_pass=""
        fi
    else
        echo "Keychain entry for $chosen_id not found on $instance_base"
    fi
else
    echo "Keychain entry for $instance_base not found"
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

if [[ ! "$chosen_secret" ]]; then
    echo "Enter password/Client Secret for $chosen_id on $instance_base"
    [[ $instance_pass ]] && echo "(or press ENTER to use existing password/Client Secret from keychain for $chosen_id)"
    read -r -s -p "Pass : " chosen_secret
    if [[ $instance_pass && ! "$chosen_secret" ]]; then
        chosen_secret="$instance_pass"
    elif [[ ! $chosen_secret ]]; then
        echo "No password/Client Secret supplied"
        exit 1
    fi
fi

# ------------------------------------------------------------------------------------
# 3. Loop through each selected instance
# ------------------------------------------------------------------------------------
echo
echo
security add-internet-password -U -s "$chosen_instance" -l "$instance_base ($chosen_id)" -a "$chosen_id" -w "$chosen_secret"
echo "Credentials for $instance_base ($chosen_id) added to keychain"

# ------------------------------------------------------------------------------------
# 4. Verify the credentials
# ------------------------------------------------------------------------------------

echo
echo "Verifying credentials for $instance_base ($chosen_id)..."
verify_credentials "$chosen_instance"
# print out version
version=$(plutil -extract version raw "$output_file_record")
if [[ $version ]]; then
    echo "Connection successful. Jamf Pro version: $version"
fi

echo
echo "Script complete"
echo
