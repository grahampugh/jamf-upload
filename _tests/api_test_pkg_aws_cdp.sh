#!/bin/bash

: <<DESCRIPTION
AWS S3 CDP package upload script
by Graham Pugh (@grahamrpugh)

1. Check for an existing package from the Classic API
2. Upload package to CDP if it's new or changed (this is tested by aws-cli using the sync command)
3. Upload the package metadata

Notes: 
Requires the aws-cli tools to be installed
User must run 'aws configure' to supply their access key, secret key and region.
DESCRIPTION

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
    echo "Usage: api_test_pkg_aws_cdp.sh --jss someserver --user username --pass password --pkg /path/to/pkg.pkg"
    echo "(don't include https:// or .jamfcloud.com)"
    echo
    echo "Use --replace to replace an existing package"
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
    if [[ expiration_epoch -gt utc_epoch_now ]]; then
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

checkExistingPackage() {
    # perform a get request on an existing package to see if it exists

    echo "Seeing if $pkg exists on the server"
    http_response=$(
        curl --request GET \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            "$url/JSSResource/packages/name/$pkg" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_record" \
            --output "$output_file_record"
    )

    echo "HTTP response: $http_response"

    if [[ $http_response -lt 350 && $http_response -ge 100 ]]; then
        pkg_id=$(plutil -extract package.id raw -expect integer "$output_file_record")
        # check that we got an integer
        if [ "$pkg_id" -eq "$pkg_id" ]; then
            echo "Existing package found: ID $pkg_id"
            if [[ $replace ]]; then
                echo "Replacing existing package"
            else
                echo "Not replacing existing package"
                exit 
            fi
        fi
    else
        # TODO - give better descriptions based on HTTP response
        echo "No existing package found: uploading as a new package"
        pkg_id=0
    fi
}

postPkg() {
    # upload the package to an S3 bucket - requires aws-cli tools and the 
    # aws bucket to have been configured using 'aws configure', supplying the access key,
    # secret key and region.
    
    # post the package
    aws s3 sync "$pkg_dir/" "s3://$s3_bucket/" --exclude "*" --include "$pkg"
}

postMetadata() {
    # post the metadata to match the package

    pkg_data="<package>
    <name>$pkg</name>
    <filename>$pkg</filename>
</package>"


    echo "Posting the package metadata to the server"
    if [[ $pkg_id -gt 0 ]]; then
        req="PUT"
    else
        req="POST"
    fi

    http_response=$(
        curl --request "$req" \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Content-Type: application/xml' \
            --data "$pkg_data" \
            "$url/JSSResource/packages/id/$pkg_id" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_record" \
            --output "$output_file_record"
    )

    echo
    echo "HTTP response: $http_response"

    if [[ "$http_response" == "10"* || "$http_response" == "20"* ]]; then
        echo "Success response ($http_response)"
    else
        echo "Fail response ($http_response)"
    fi
}

## ---------------------------------------------------------------
## START

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
        --s3)
            shift
            s3_bucket="$1"
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

# upload the package (aws-cli sync will check if it's different)
postPkg

# post the package metadata to Jamf Pro
postMetadata

## ---------------------------------------------------------------
## END

# finish up by expiring the token
echo 
invalidateToken
rm "$output_file_token"
