#!/bin/zsh

# --------------------------------------------------------------------------------
# Script to create a jamf-cli profile for the Jamf Platform API.
#
# If swiftDialog is present, shows a GUI form (pre-filled with any CLI args).
# If swiftDialog is absent, prompts interactively in the terminal for any
# values not supplied via CLI arguments.
# Use --no-dialog to skip the GUI entirely and require all values via flags.
#
# The resulting profile can be used with jamf-upload.sh via:
#   jamf-upload.sh --jamf-cli-profile <profile-name> ...
# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------------------------------

usage() {
    cat <<'USAGE'
Usage:
./set-jamf-cli-platform-profile.sh       - interactive (swiftDialog UI if available)

Options:
--profile PROFILE_NAME                   - profile name for jamf-cli
-r | --region (eu|us|apac)               - region the tenant is hosted in
-t | --tenant TENANT_ID                  - tenant ID (UUID)
-e | --environment ENVIRONMENT_ID        - environment ID (UUID); takes precedence over --tenant
--id | --client-id CLIENT_ID             - API client ID
--secret | --client-secret CLIENT_SECRET - API client secret
--no-dialog                              - non-interactive: all values must be supplied via flags
-v                                       - verbose output

USAGE
}

region_to_url() {
    case "$1" in
        us)   echo "https://us.api.jamfcloud.com" ;;
        eu)   echo "https://eu.api.jamfcloud.com" ;;
        apac) echo "https://apac.api.jamfcloud.com" ;;
        *)
            echo "   [region_to_url] ERROR: Invalid region '$1'. Use one of: us, eu, apac." >&2
            return 1
            ;;
    esac
}

collect_via_dialog() {
    # Build textfield args, pre-filling any values already supplied via CLI
    local profile_arg="Profile Name,required"
    [[ -n "$profile_name" ]] && profile_arg+=",value=$profile_name"

    # a single ID field is used for either the tenant or environment id; the
    # "Level" selector determines which it is (environment takes precedence)
    local level_default="tenant"
    local id_value="$tenant_id"
    if [[ -n "$environment_id" ]]; then
        level_default="environment"
        id_value="$environment_id"
    fi
    local id_arg="Tenant/Environment ID,required"
    [[ -n "$id_value" ]] && id_arg+=",value=$id_value"

    local clientid_arg="Client ID,required"
    [[ -n "$client_id" ]] && clientid_arg+=",value=$client_id"

    local secret_arg="Client Secret,required,secure"
    # swiftDialog does not support pre-filling secure fields for security reasons

    local region_default="${chosen_region:-eu}"

    local dialog_result
    dialog_result=$(dialog \
        --title "Add Jamf Platform API Profile" \
        --message "Enter the credentials for the Jamf Platform API. The profile will be stored by jamf-cli and can be used with jamf-upload." \
        --textfield "$profile_arg" \
        --selecttitle "Region" \
        --selectvalues "eu,us,apac" \
        --selectdefault "$region_default" \
        --selecttitle "Level" \
        --selectvalues "tenant,environment" \
        --selectdefault "$level_default" \
        --textfield "$id_arg" \
        --textfield "$clientid_arg" \
        --textfield "$secret_arg" \
        --button1text "Add Profile" \
        --button2text "Cancel" \
        --height 500 \
        --json 2>/dev/null)

    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo "   [main] Cancelled."
        exit 0
    fi

    local tmp_json
    tmp_json=$(mktemp /tmp/jamf_cli_profile_dialog_XXXXXX.json)
    echo "$dialog_result" > "$tmp_json"

    profile_name=$(plutil -extract "Profile Name" raw "$tmp_json" 2>/dev/null)
    chosen_region=$(plutil -extract "Region.selectedValue" raw "$tmp_json" 2>/dev/null)
    platform_level=$(plutil -extract "Level.selectedValue" raw "$tmp_json" 2>/dev/null)
    local id_value
    id_value=$(plutil -extract "Tenant/Environment ID" raw "$tmp_json" 2>/dev/null)
    client_id=$(plutil -extract "Client ID" raw "$tmp_json" 2>/dev/null)
    client_secret=$(plutil -extract "Client Secret" raw "$tmp_json" 2>/dev/null)

    rm -f "$tmp_json"

    # map the single ID field onto the chosen level
    if [[ "$platform_level" == "environment" ]]; then
        environment_id="$id_value"
        tenant_id=""
    else
        tenant_id="$id_value"
        environment_id=""
    fi

    chosen_region="${chosen_region:l}"
}

collect_via_terminal() {
    echo
    echo "Enter values for the Jamf Platform API profile (press ENTER to keep existing value where shown)."
    echo

    if [[ -z "$profile_name" ]]; then
        read -r "profile_name?Profile Name: "
        [[ -z "$profile_name" ]] && { echo "   [main] No profile name supplied."; exit 1; }
    fi

    if [[ -z "$chosen_region" ]]; then
        read -r "chosen_region?Region (eu/us/apac) [eu]: "
        chosen_region="${chosen_region:-eu}"
    fi
    chosen_region="${chosen_region:l}"
    # validate region
    region_to_url "$chosen_region" &>/dev/null || exit 1

    # only prompt for an ID if neither a tenant nor an environment id was supplied
    if [[ -z "$tenant_id" && -z "$environment_id" ]]; then
        local platform_level
        read -r "platform_level?Level (tenant/environment) [tenant]: "
        platform_level="${platform_level:-tenant}"
        platform_level="${platform_level:l}"
        if [[ "$platform_level" == "environment" ]]; then
            read -r "environment_id?Environment ID: "
            [[ -z "$environment_id" ]] && { echo "   [main] No environment ID supplied."; exit 1; }
        else
            read -r "tenant_id?Tenant ID: "
            [[ -z "$tenant_id" ]] && { echo "   [main] No tenant ID supplied."; exit 1; }
        fi
    fi

    if [[ -z "$client_id" ]]; then
        read -r "client_id?Client ID: "
        [[ -z "$client_id" ]] && { echo "   [main] No client ID supplied."; exit 1; }
    fi

    if [[ -z "$client_secret" ]]; then
        read -rs "client_secret?Client Secret: "
        echo
        [[ -z "$client_secret" ]] && { echo "   [main] No client secret supplied."; exit 1; }
    fi
}

create_profile() {
    local api_url
    api_url=$(region_to_url "$chosen_region") || return 1

    # environment id takes precedence over tenant id
    local level_flag level_id
    if [[ -n "$environment_id" ]]; then
        level_flag="--environment-id"
        level_id="$environment_id"
    else
        level_flag="--tenant-id"
        level_id="$tenant_id"
    fi

    if [[ $verbose -eq 1 ]]; then
        echo "   [create_profile] Creating jamf-cli profile '$profile_name' for $api_url ($level_flag $level_id)"
    fi

    # jamf-cli reads the client secret with no-echo (requires a TTY), so use expect
    local expect_output
    expect_output=$(/usr/bin/expect -c "
        log_user 0
        spawn jamf-cli config add-profile \
            --auth-method platform \
            $level_flag {$level_id} \
            --url {$api_url} \
            {$profile_name}
        expect -re {[Cc]lient.?[Ii][Dd]}
        send {$client_id}
        send \"\r\"
        expect -re {[Cc]lient.?[Ss]ecret}
        send {$client_secret}
        send \"\r\"
        expect eof
        catch wait result
        exit [lindex \$result 3]
    " 2>&1)
    local expect_exit=$?

    if [[ $expect_exit -eq 0 ]]; then
        echo "   [create_profile] Profile '$profile_name' created successfully"
    else
        echo "   [create_profile] ERROR: jamf-cli config add-profile failed (exit $expect_exit)"
        [[ $verbose -eq 1 && -n "$expect_output" ]] && echo "$expect_output"
        return 1
    fi
}

verify_profile() {
    local profile_name="$1"
    local tmp_token
    tmp_token=$(mktemp /tmp/jamf_cli_token_XXXXXX.json)

    if [[ $verbose -eq 1 ]]; then
        echo "   [verify_profile] Verifying profile '$profile_name' by requesting a token"
    fi

    if jamf-cli platform auth token --profile "$profile_name" > "$tmp_token" 2>/dev/null; then
        local token
        token=$(plutil -extract token raw "$tmp_token" 2>/dev/null)
        rm -f "$tmp_token"
        if [[ -n "$token" ]]; then
            echo "   [verify_profile] Token successfully retrieved for profile '$profile_name'"
            return 0
        else
            echo "   [verify_profile] ERROR: Token request succeeded but no token found in response"
            return 1
        fi
    else
        rm -f "$tmp_token"
        echo "   [verify_profile] ERROR: Failed to obtain token for profile '$profile_name'"
        return 1
    fi
}

show_result_dialog() {
    local success="$1"
    if [[ "$success" == "true" ]]; then
        dialog \
            --title "Profile Added" \
            --message "The jamf-cli profile **$profile_name** was created and verified successfully.\n\nYou can now use it with jamf-upload:\n\`jamf-upload.sh --jamf-cli-profile $profile_name ...\`" \
            --button1text "OK" \
            --icon "SF=checkmark.circle.fill,colour=green" \
            --json &>/dev/null
    else
        dialog \
            --title "Profile Creation Failed" \
            --message "The jamf-cli profile **$profile_name** could not be created or verified.\n\nPlease check your credentials and try again." \
            --button1text "OK" \
            --icon "SF=xmark.circle.fill,colour=red" \
            --json &>/dev/null
    fi
}

# --------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------

verbose=0
no_dialog="false"

while test $# -gt 0; do
    case "$1" in
        --profile)
            shift
            profile_name="$1"
            ;;
        -r|--region)
            shift
            chosen_region="$1"
            ;;
        -t|--tenant|--tenant-id)
            shift
            tenant_id="$1"
            ;;
        -e|--environment|--environment-id)
            shift
            environment_id="$1"
            ;;
        --id|--client-id)
            shift
            client_id="$1"
            ;;
        --secret|--client-secret)
            shift
            client_secret="$1"
            ;;
        --no-dialog)
            no_dialog="true"
            ;;
        -v)
            verbose=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

# jamf-cli is always required
if ! command -v jamf-cli &>/dev/null; then
    echo "   [main] ERROR: jamf-cli not found. Please install jamf-cli and try again."
    exit 1
fi

if [[ "$no_dialog" == "true" ]]; then
    # Strict mode: all values must be supplied via flags
    missing=()
    [[ -z "$profile_name" ]]  && missing+=("--profile")
    [[ -z "$chosen_region" ]] && missing+=("--region")
    [[ -z "$tenant_id" && -z "$environment_id" ]] && missing+=("--tenant or --environment")
    [[ -z "$client_id" ]]     && missing+=("--client-id")
    [[ -z "$client_secret" ]] && missing+=("--client-secret")
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "   [main] ERROR: Missing required options: ${missing[*]}"
        usage
        exit 1
    fi
    chosen_region="${chosen_region:l}"
    region_to_url "$chosen_region" &>/dev/null || exit 1
elif command -v dialog &>/dev/null; then
    # swiftDialog available: show GUI, pre-filled with any CLI-supplied values
    collect_via_dialog
else
    # No swiftDialog: prompt in terminal for any missing values
    echo "   [main] swiftDialog not found — using terminal prompts."
    collect_via_terminal
fi

if ! create_profile; then
    command -v dialog &>/dev/null && [[ "$no_dialog" != "true" ]] && show_result_dialog "false"
    exit 1
fi

if ! verify_profile "$profile_name"; then
    command -v dialog &>/dev/null && [[ "$no_dialog" != "true" ]] && show_result_dialog "false"
    exit 1
fi

command -v dialog &>/dev/null && [[ "$no_dialog" != "true" ]] && show_result_dialog "true"

echo
echo "Script complete"
echo
