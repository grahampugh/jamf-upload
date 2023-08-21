#!/bin/bash

: <<DOC
Script for testing Jamf API dbfileupload endpoint using curl

DOC

usage() {
    echo "Usage: api_test_pkg.sh --jss someserver --user username --pass password --pkg /path/to/pkg.pkg --id NN"
    echo "(don't include https:// or .jamfcloud.com)"
    echo "ID is used to overwrite an existing package"
}

# default ID for a new package
pkg_id=-1

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
        --id)
            shift
            pkg_id="$1"
            ;;
        *)
            usage
            exit
            ;;
    esac
    shift
done

if [[ ! $jss || ! $user || ! $pass || ! $pkg_path  ]]; then
    usage
    exit
fi

temp_file="/tmp/api_tests.txt"

url="https://$jss.jamfcloud.com"

# generate a b64 hash of the credentials
credentials=$(printf "%s" "$user:$pass" | iconv -t ISO-8859-1 | base64 -i -)

# now try to post a package 
echo 

pkg=$(basename "$pkg_path")
http_response=$(
    curl --request POST \
        --header "authorization: Basic $credentials" \
        --header 'Accept: application/xml' \
        --header 'DESTINATION: 0' \
        --header "OBJECT_ID: $pkg_id" \
        --header 'FILE_TYPE: 0' \
        --header "FILE_NAME: $pkg" \
        --upload-file "$pkg_path" \
        -i -o /dev/null \
        --write-out %{http_code} \
        "$url/dbfileupload"
)

echo
echo "HTTP response: $http_response"
