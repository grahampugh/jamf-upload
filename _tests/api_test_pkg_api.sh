#!/bin/bash

: <<DOC
Upload a package using the Jamf Pro API using curl

Actions:
- Checks if we already have a token
- Grabs a new token if required using basic auth
- Works out the Jamf Pro version
- Performs a GET request on a supplied package object using the bearer token
- Uploads a package using the bearer token
- If that fails, uploads a package using basic auth
DOC

## ---------------------------------------------------------------
## VARIABLES

# declarations
token=""
expiration_epoch="0"

# files
output_location="/tmp/api_tests"
mkdir -p "$output_location"
cookie_jar="$output_location/cookie_jar.txt"
headers_file_session="$output_location/headers_session.txt"
headers_file_token="$output_location/headers_token.txt"
headers_file_record="$output_location/headers_record.txt"
headers_file_list="$output_location/headers_list.txt"
headers_file_delete="$output_location/headers_delete.txt"
output_file_session="$output_location/output_session.txt"
output_file_token="$output_location/output_token.txt"
output_file_record="$output_location/output_record.txt"
output_file_list="$output_location/output_list.txt"
output_file_delete="$output_location/output_delete.txt"

## ---------------------------------------------------------------
## FUNCTIONS

usage() {
    echo "Usage: api_test_pkg_api.sh --jss someserver --user username --pass password --pkg /path/to/pkg.pkg"
    echo "(don't include https:// or .jamfcloud.com)"
}

getBearerToken() {
    # generate a b64 hash of the credentials
    credentials=$(printf "%s" "$user:$pass" | iconv -t ISO-8859-1 | base64 -i -)

    # request the token
    http_response=$(
        curl --request POST \
        --silent \
        --header "authorization: Basic $credentials" \
        --url "$url/api/v1/auth/token" \
        --write-out "%{http_code}" \
        --header 'Accept: application/json' \
        --cookie-jar "$cookie_jar" \
        --dump-header "$headers_file_token" \
        --output "$output_file_token"
    )
    echo "HTTP response: $http_response"
}

checkTokenExpiration() {
    if [[ -f "$output_file_token" ]]; then
        echo "Token file found"
        token=$(plutil -extract token raw "$output_file_token")
        expires=$(plutil -extract expires raw "$output_file_token" | awk -F . '{print $1}')
        expiration_epoch=$(date -j -f "%Y-%m-%dT%T" "$expires" +"%s")
    else
        echo "No token file found"
    fi

    utc_epoch_now=$(date -j -f "%Y-%m-%dT%T" "$(date -u +"%Y-%m-%dT%T")" +"%s")
    if [[ $expiration_epoch -gt $utc_epoch_now ]]; then
        echo "Token valid until the following epoch time: " "$expiration_epoch"
    else
        echo "No valid token available, getting new token"
        getBearerToken
        token=$(plutil -extract token raw "$output_file_token")
    fi
}

invalidateToken() {
    response=$(curl -w "%{http_code}" -H "Authorization: Bearer $token" "$url/api/v1/auth/invalidate-token" -X POST -s -o /dev/null)
    if [[ $response == 204 ]]; then
        echo "Token successfully invalidated"
        token=""
        expiration_epoch="0"
    elif [[ $response == 401 ]]; then
        echo "Token already invalid"
    else
        echo "An unknown error occurred invalidating the token"
    fi
}

encode_pkg_name() {
    pkg_name_encoded="$( echo "$pkg" | sed -e 's| |%20|g' | sed -e 's|&amp;|%26|g' )"
}

checkExistingPackage() {
    # perform a get request on an existing package to see if it exists

    echo "Seeing if $pkg exists on the server"
    encode_pkg_name

    http_response=$(
        curl --request GET \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            "$url/api/v1/packages/?filter=packageName%3D%3D%22$pkg_name_encoded%22" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_record" \
            --output "$output_file_record"
    )

    echo "HTTP response: $http_response"

    if [[ $http_response -lt 400 && $http_response -ge 100 ]]; then
        # cat "$output_file_record" # TEMP
        pkg_count=$(plutil -extract totalCount raw -expect integer "$output_file_record")
        if [[ $pkg_count -gt 0 ]]; then
            pkg_id=$(plutil -extract results.0.id raw -expect string "$output_file_record")
            # check that we got an integer
            if [[ "$pkg_id" -gt 0 ]]; then
                echo "Existing package found: ID $pkg_id"
                if [[ $replace -eq 1 ]]; then
                    echo "Replacing existing package"
                else
                    echo "Not replacing existing package"
                    exit 
                fi
            else
                echo "No existing package found: uploading as a new package"
                pkg_id=0
            fi
        else
            echo "No existing package found: uploading as a new package"
            pkg_id=0
        fi
    else
        echo "No existing package found: uploading as a new package"
        pkg_id=0
    fi
}

postPkgMetadata() {

    echo
    echo "Posting package as ID $pkg_id"

    read -d '' -r data_json <<JSON
    {
        "packageName": "$pkg",
        "fileName": "$pkg",
        "categoryId": "-1",
        "priority": 3,
        "fillUserTemplate": false,
        "uninstall": false,
        "rebootRequired": false,
        "osInstall": false,
        "suppressUpdates": false,
        "suppressFromDock": false,
        "suppressEula": false,
        "suppressRegistration": false
    }
JSON

    # echo "$data_json" # TEMP

    echo "Posting the package metadata to the server"
    if [[ $pkg_id -gt 0 ]]; then
        req="PUT"
        jss_url="$url/api/v1/packages/$pkg_id"
    else
        req="POST"
        jss_url="$url/api/v1/packages"
    fi

    http_response=$(
        curl --request "$req" \
            --header "authorization: Bearer $token" \
            --header 'Content-Type: application/json' \
            --header 'Accept: application/json' \
            --data "$data_json" \
            "$jss_url" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_record" \
            --output "$output_file_record"
    )

    echo
    echo "HTTP response: $http_response"

    if [[ "$http_response" == "10"* || "$http_response" == "20"* ]]; then
        pkg_id=$(plutil -extract id raw -expect string "$output_file_record")
        # check that we got an integer
        if [ "$pkg_id" -eq "$pkg_id" ]; then
            echo "Package ID: $pkg_id"
        fi
    else
        echo "Fail response ($http_response)"
        echo
        echo "HEADERS:"
        cat "$headers_file_record"
        echo
        echo "OUTPUT:"
        cat "$output_file_record"
        echo
        echo "DATA:"
        echo
        exit 1
    fi
}

postPkg() {
    # upload the package

    echo "URL: $url/api/v1/packages/$pkg_id/upload" # TEMP

    http_response=$(
        curl --request "POST" \
            --header "authorization: Bearer $token" \
            --header 'Content-Type: multipart/form-data' \
            --header 'Accept: application/json' \
            --form "file=@$pkg_path" \
            "$url/api/v1/packages/$pkg_id/upload" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_record" \
            --output "$output_file_record"
    )

    echo
    echo "HTTP response: $http_response"

    if [[ "$http_response" == "10"* || "$http_response" == "20"* || "$http_response" == "3"* ]]; then
        echo "Success response ($http_response)"
    else
        echo "Fail response ($http_response)"
        echo
        echo "HEADERS:"
        cat "$headers_file_record"
        echo
        echo "OUTPUT:"
        cat "$output_file_record"
        echo
    fi
}


## MAIN

# default to not replace existing package
replace=0

while test $# -gt 0 ; do
    case "$1" in
        -s|--jss)
            shift
            jss="$1"
            ;;
        -u|--user)
            shift
            user="$1"
            ;;
        -p|--pass)
            shift
            pass="$1"
            ;;
        -f|--pkg)
            shift
            pkg_path="$1"
            ;;
        --replace)
            shift
            replace=1
            ;;
        *)
            usage
            exit
            ;;
    esac
    shift
done

if [[ ! $jss || ! $user || ! $pass || ! $pkg_path ]]; then
    usage
    exit
fi

# set URL
url="https://$jss.jamfcloud.com"

# set pkg name
pkg=$(basename "$pkg_path")
pkg_dir=$(dirname "$pkg_path")

# grab a token
checkTokenExpiration

## ---------------------------------------------------------------
## MAIN

# check there's an existing package in Jamf Pro
checkExistingPackage

# upload the package
postPkgMetadata
postPkg

## ---------------------------------------------------------------
## END

# finish up by expiring the token
echo 
invalidateToken
rm "$output_file_token"
