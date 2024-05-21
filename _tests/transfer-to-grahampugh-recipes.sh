#!/bin/bash

# copy JamfUploaderProcessors changes to grahampugh-recipes

source_folder="$HOME/sourcecode"

# 1. check branches and confirm to proceed
if echo "jamf-upload:" && git -C "$source_folder/jamf-upload" status -sb && echo "grahampugh-recipes:" && git -C "$source_folder/grahampugh-recipes" status -sb; then
    printf '%s' "WARNING! This will overwrite "$source_folder/grahampugh-recipes/JamfUploaderProcessors". Are you sure? (Y/N) : "
    read -r are_you_sure < /dev/tty
    case "$are_you_sure" in
        Y|y)
            echo "Confirmed, proceeding"
        ;;
        *)
            echo "Declined, quitting"
            exit 0
        ;;
    esac
else
    echo "ERROR connecting to remote repo"
    exit 1
fi   


# 2. ensure repos are up-to-date

if git -C "$source_folder/jamf-upload" pull; then
    echo "jamf-upload repo up to date"
else
    echo "ERROR: repo could not be pulled, aborting"
    exit 1
fi

if git -C "$source_folder/grahampugh-recipes" pull; then
    echo "jamf-upload repo up to date"
else
    echo "ERROR: repo could not be pulled, aborting"
    exit 1
fi

# 2. copy
echo "Copying JamfUploaderProcessors folder"
if cp -r "$source_folder/jamf-upload/JamfUploaderProcessors" "$source_folder/grahampugh-recipes/"; then
    echo "Copying was successful, now proceed to commit and push (manual process)"
else
    echo "ERROR with copying the JamfUploaderProcessors folder - check and retry"
    exit 1
fi

