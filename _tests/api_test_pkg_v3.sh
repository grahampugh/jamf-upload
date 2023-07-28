#!/bin/bash

: <<DOC
Script for testing Jamf API direct (v3) endpoint using curl
DOC

usage() {
    echo "Usage: api_test_pkg_v3.sh --jss someserver --user username --pass password --pkg /path/to/pkg.pkg"
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

# temp files
output_location="/tmp/api_tests"
mkdir -p "$output_location"
cookie_jar="$output_location/cookie_jar.txt"
headers_file_session="$output_location/headers_session.txt"
headers_file_token="$output_location/headers_token.txt"
headers_file_upload="$output_location/headers_upload.txt"
headers_file_record="$output_location/headers_record.txt"
output_file_session="$output_location/output_session.txt"
output_file_token="$output_location/output_token.txt"
output_file_upload="$output_location/output_upload.txt"
output_file_record="$output_location/output_record.txt"

url="https://$jss.jamfcloud.com"

echo
echo "---------------------------------------------------"
echo "PART 1: Create Session"
echo "---------------------------------------------------"
echo

# 1. create session
curl --request POST \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$user" \
    --data-urlencode "password=$pass" \
    --location \
    --cookie-jar "$cookie_jar" \
    --dump-header "$headers_file_session" \
    --output "$output_file_session" \
    "$url"

JSESSIONID=$(grep JSESSIONID "$headers_file_session" | head -n 1 | cut -d' ' -f2 | sed 's|JSESSIONID=||' | sed 's|;||')
APBALANCEID=$(grep APBALANCEID "$headers_file_session" | head -n 1 | cut -d' ' -f2 | sed 's|APBALANCEID=||' | sed 's|;||')
AWSALB=$(grep AWSALB "$headers_file_session" | head -n 1 | cut -d' ' -f2 | sed 's|AWSALB=||' | sed 's|;||')
AWSALBCORS=$(grep AWSALBCORS "$headers_file_session" | head -n 1 | cut -d' ' -f2 | sed 's|AWSALBCORS=||' | sed 's|;||')

echo "JSESSIONID = $JSESSIONID"
echo "APBALANCEID = $APBALANCEID"
echo "AWSALB = $AWSALB"
echo "AWSALBCORS = $AWSALBCORS"

echo
echo "---------------------------------------------------"
echo "PART 2: Get upload token"
echo "---------------------------------------------------"
echo


# 2. get an upload token
curl --request GET \
    --location \
    --cookie "$cookie_jar" \
    --cookie-jar "$cookie_jar" \
    -D "$headers_file_token" \
    --output "$output_file_token" \
    "$url/legacy/packages.html?id=-1&o=c"

echo ""
# echo "HEADERS:"
# cat "$headers_file_token"

SESSION_TOKEN=$(sed -n 's/.*<input type="hidden" name="session-token" id="session-token" value="\([a-zA-Z0-9]*\)">.*/\1/p' "$output_file_token")
X_AUTH_TOKEN=$(sed -n 's/.*xhr.setRequestHeader("X-Auth-Token", "\([a-zA-Z0-9]*\)");.*/\1/p' "$output_file_token")
UPLOAD_BASE_URL=$(sed -n 's/.*const url = "\(.*\)" + encodeURI(file.name);/\1/p' "$output_file_token")

echo "SESSION_TOKEN = $SESSION_TOKEN"
echo "X_AUTH_TOKEN = $X_AUTH_TOKEN"
echo "UPLOAD_BASE_URL = $UPLOAD_BASE_URL"

echo
echo "---------------------------------------------------"
echo "PART 3: Post package"
echo "---------------------------------------------------"
echo


# 3. post a package 
pkg_name=$(basename "$pkg_path")

pkg_name_url="${pkg_name// /%20}"

curl "$UPLOAD_BASE_URL/$pkg_name_url" \
    -H "x-auth-token: $X_AUTH_TOKEN" \
    -H 'accept: */*' \
    -H "origin: $url" \
    -H "referer: $url" \
    -F "file=@$pkg_path;filename=$pkg_name" \
    -D "$headers_file_upload" \
    --output "$output_file_upload" \
    --cookie "$cookie_jar" \
    --cookie-jar "$cookie_jar" \
    --compressed

echo
echo "---------------------------------------------------"
echo "PART 4: Record the package in Jamf"
echo "---------------------------------------------------"
echo


# 4. Record the file in Jamf
pkg_name_data_raw="${pkg_name// /+}"
curl "$url/legacy/packages.html?id=$pkg_id&o=c" \
    -H "origin: $url" \
    -H 'content-type: application/x-www-form-urlencoded' \
    -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' \
    -H "referer: $url/legacy/packages.html?id=$pkg_id&o=c" \
    --data-raw "session-token=$SESSION_TOKEN&lastTab=General&lastSideTab=null&lastSubTab=null&lastSubTabSet=null&name=$pkg_name_data_raw&categoryID=12&fileInputfileName=$pkg_name_data_raw&fileName=$pkg_name_data_raw&resetFIELD_MANIFEST_INPUT=&info=JamfUploader&notes=$(date)&priority=9&uninstall_disabled=false&osRequirements=&action=Save" \
    -D "$headers_file_record" \
    --output "$output_file_record" \
    --compressed \
    --cookie "$cookie_jar" \
    --cookie-jar "$cookie_jar"
