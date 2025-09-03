#!/bin/bash

# test script for Jira issues. 
# Parameters:
# $1 - subdomain (without .atlassian.net)
# $2 - username (email address)
# $3 - API token (generated in Jira)
# $4 - project id

subdomain="$1"
USERNAME="$2"
API_TOKEN="$3"
project_id="$4"

issuetype_id="10001"
priority_id="2"
description="Please ignore this issue. This is a test issue created by $USERNAME using a script to test Jira integration."
summary="Test issue created by $USERNAME"


token=$(echo -n $USERNAME:$API_TOKEN | base64)
echo "Using token: $token"

template='{

  "fields": {
    "summary": "%s",
    "issuetype": {
      "id": "%s"
    },
    "project": {
      "id": "%s"
    },
    "priority": {
      "id": "%s"
    },
    
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "text": "%s",
              "type": "text"
            }
          ]
        }
      ]
    }
  }
}'

json_final=$(printf "$template" \
		    "$summary" \
		    "$issuetype_id" \
		    "$project_id" \
		    "$priority_id" \
		    "$description")

curl --location -X POST \
	  -H "Authorization: Basic $token" \
	  -H "Content-Type:application/json" \
	  "https://$subdomain.atlassian.net/rest/api/3/issue/" \
	  -d \
	  "$json_final"
	  