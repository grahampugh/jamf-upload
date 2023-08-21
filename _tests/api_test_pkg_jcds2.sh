#!/bin/bash

: <<DESCRIPTION
JCDS2 package upload script
by Graham Pugh (@grahamrpugh)

1. Get a bearer token
2. Check for an existing package from the Classic API
3. Check for an existing package from the JCDS endpoint
4. Check that the checksum matches our local pkg
5. Delete the existing package from the JCDS if the checksum doesn't match
6. Upload package to JCDS if it's new or the existing has been deleted (but not if it has the same hash)
7. Upload the package metadata

Note: requires the aws-cli tools to be installed
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
    echo "Usage: api_test_pkg_jcds2.sh --jss someserver --user username --pass password --pkg /path/to/pkg.pkg"
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

deleteExistingPkg() {
    # delete the existing package
    echo "Deleting $pkg from JCDS"
    http_response=$(
        curl --request DELETE \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            "$url/api/v1/jcds/files/$pkg" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_delete" \
            --output "$output_file_delete"
    )
    echo "HTTP response: $http_response"
}

checkJCDS() {
    # list all the packages
    echo "Getting a list of packages from JCDS"
    http_response=$(
        curl --request GET \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            "$url/api/v1/jcds/files" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_list" \
            --output "$output_file_list"
    )
    echo "HTTP response: $http_response"

    if [[ $http_response -eq 200 ]]; then
        # convert the list to a plist so we can actually work with it in bash
        plutil -convert xml1 "$output_file_list"

        # count the number of items in the list
        pkg_count=$(grep -c fileName "$output_file_list")

        # loop through each item in the JSON response
        jcds_pkg=""
        jcds_pkg_md5=0  # assign empty value to avoid errors
        for ((i=1; i<=pkg_count; i++)); do
            jcds_pkg=$(/usr/libexec/PlistBuddy -c "Print :$i:fileName" "$output_file_list")
            if [[ "$jcds_pkg" == "$pkg" ]]; then
                jcds_pkg_md5=$(/usr/libexec/PlistBuddy -c "Print :$i:md5" "$output_file_list")
                break
            fi
        done

        # also find out the sha3 of the local package
        pkg_md5=$(md5 -q "$pkg_path")
                
        # now compare the two
        if [[ "$jcds_pkg_md5" ]]; then
            echo "Existing package found: URL $jcds_pkg"
            if [[ $replace ]]; then
                # Check if the MD5 hash matches (Mac's LibreSSL can't do SHA3-512)
                # If not, we want to replace it, which has to be done 
                # by deleting and uploading new
                if [[ "$jcds_pkg_md5" == "$pkg_md5" ]]; then
                    echo "MD5 matches so not replacing existing package on JCDS"
                    replace_jcds_pkg=0
                else
                    echo "MD5 hash doesn't match. Replacing existing package on JCDS"
                    replace_jcds_pkg=1
                fi
            else
                echo "Not replacing existing package on JCDS"
                replace_jcds_pkg=0
            fi
        fi
    else
        echo "No existing package found: uploading as a new package"
    fi
}

getPkgUploadToken() {
    # get an access token to a package to the JCDS
    echo "Getting a package upload token from JCDS"
    http_response=$(
        curl --request POST \
            --silent \
            --header "authorization: Bearer $token" \
            --header 'Accept: application/json' \
            --header 'Content-Type: application/json' \
            "$url/api/v1/jcds/files" \
            --write-out "%{http_code}" \
            --location \
            --cookie-jar "$cookie_jar" \
            --dump-header "$headers_file_session" \
            --output "$output_file_session" \
    )
    echo
    echo "HTTP response: $http_response"
}

postPkg() {
    # upload the package to an S3 bucket - requires aws-cli tools

    # set the required configurations (delete these afterwards)
    default_access_key=$(plutil -extract accessKeyID raw "$output_file_session")
    default_secret_key=$(plutil -extract secretAccessKey raw "$output_file_session")
    aws_session_token=$(plutil -extract sessionToken raw "$output_file_session")
    region=$(plutil -extract region raw "$output_file_session")
    s3_bucket=$(plutil -extract bucketName raw "$output_file_session")
    s3_path=$(plutil -extract path raw "$output_file_session")

    # add the configuration to the aws-cli config file
    aws configure set aws_access_key_id "$default_access_key"
    aws configure set aws_secret_access_key "$default_secret_key"
    aws configure set aws_session_token "$aws_session_token"
    aws configure set default.region "$region"

    # post the package
    aws s3 cp "$pkg_path" "s3://$s3_bucket/$s3_path" --region "$region"

    # delete credentials from the aws-cli config file
    aws configure set aws_access_key_id ""
    aws configure set aws_secret_access_key ""
    aws configure set aws_session_token ""
    aws configure set default.region ""
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

# grab a token
checkTokenExpiration

## ---------------------------------------------------------------
## MAIN

# check there's an existing package in Jamf Pro
checkExistingPackage

# check if that same package exists in JCDS
checkJCDS

# if --replace and the package metadata doesn't match, delete the existing package from the JCDS
if [[ $replace_jcds_pkg -eq 1 ]]; then
    deleteExistingPkg
fi

# upload the package if it's new or we just deleted the existing one
if [[ ! "$jcds_pkg_md5" || $replace_jcds_pkg -eq 1 ]]; then
    getPkgUploadToken
    postPkg
fi

# post the package metadata to Jamf Pro
postMetadata

## ---------------------------------------------------------------
## END

# finish up by expiring the token
echo 
invalidateToken
rm "$output_file_token"
