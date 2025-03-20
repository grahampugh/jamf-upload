#!/bin/bash

# Define the JSON file path
JSON_FILE="$1"

# Loop through each object in the JSON file
jq -c '.[]' "$JSON_FILE" | while read -r obj; do
    id=$(echo "$obj" | jq -r '.id')
    name=$(echo "$obj" | jq -r '.name')

    # Run the autopkg command with the extracted values
    echo OBJECT_ID="$id" 
    echo NEW_NAME="$name"
    autopkg run -vv _ChangePolicyNameTest.jamf.recipe.yaml --key OBJECT_ID="$id" --key NEW_NAME="$name"
done