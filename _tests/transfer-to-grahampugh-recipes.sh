#!/bin/bash

# copy JamfUploaderProcessors changes to grahampugh-recipes

source_folder="$HOME/sourcecode"

# 1. ensure repos are up-to-date

git -C "$source_folder/jamf-upload" pull
git -C "$source_folder/grahampugh-recipes" pull

# 2. copy

cp -r "$source_folder/jamf-upload/JamfUploaderProcessors" "$source_folder/grahampugh-recipes/JamfUploaderProcessors"

