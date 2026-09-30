#!/bin/bash

###############################################################################
# Script Name: set_version.sh
# Description: Updates __version__ in JamfUploaderBase.py to today's date
#              (YYYY.MM.DD.N), commits the change and pushes it to GitHub.
#              If the version is already today's date, N is incremented;
#              otherwise it is reset to 0.
#              If the current branch is main, a new branch named
#              set-version-<version> is created for the commit instead.
# Usage: ./_tests/set_version.sh
###############################################################################

set -euo pipefail

# Get the script directory and navigate to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

VERSION_FILE="JamfUploaderProcessors/JamfUploaderLib/JamfUploaderBase.py"

# check that gh is installed and authenticated
if ! command -v gh &>/dev/null; then
    echo "ERROR: gh is required but not installed. Please install gh and try again."
    exit 1
fi
if ! gh auth status &>/dev/null; then
    echo "ERROR: gh is not authenticated. Run 'gh auth login' and try again."
    exit 1
fi

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "ERROR: $VERSION_FILE not found"
    exit 1
fi

# don't sweep unrelated edits to the version file into the version commit
if ! git diff --quiet HEAD -- "$VERSION_FILE"; then
    echo "ERROR: $VERSION_FILE has uncommitted changes. Commit or stash them first."
    exit 1
fi

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" == "HEAD" ]]; then
    echo "ERROR: HEAD is detached. Check out a branch first."
    exit 1
fi

# Get today's date in YYYY.MM.DD format
TODAY=$(date +%Y.%m.%d)

# Extract the current __version__ value
current_version=$(sed -n -E 's/^[[:space:]]*__version__ = "([^"]*)".*/\1/p' "$VERSION_FILE" | head -n1)
if [[ -z "$current_version" ]]; then
    echo "ERROR: No __version__ string found in $VERSION_FILE"
    exit 1
fi
current_date_part="${current_version%.*}"
current_minor_part="${current_version##*.}"

if [[ "$current_date_part" == "$TODAY" ]]; then
    # Same date, bump minor version
    new_version="$TODAY.$((current_minor_part + 1))"
else
    # New date, reset minor version to 0
    new_version="$TODAY.0"
fi

echo "Repository root: $REPO_ROOT"
echo "Current version: $current_version"
echo "New version:     $new_version"
echo ""

# main is protected, so never commit directly to it. If that's the current
# branch, create and switch to a version-named branch first.
if [[ "$current_branch" == "main" ]]; then
    new_branch="set-version-$new_version"
    if git show-ref --verify --quiet "refs/heads/$new_branch"; then
        echo "ERROR: Branch $new_branch already exists."
        exit 1
    fi
    git checkout -b "$new_branch"
    echo "  Created and switched to new branch: $new_branch"
    current_branch="$new_branch"
fi

# Update the __version__ line
sed -i '' -E "s/^([[:space:]]*__version__ = )\"[^\"]*\"/\1\"$new_version\"/" "$VERSION_FILE"
if ! grep -q "__version__ = \"$new_version\"" "$VERSION_FILE"; then
    echo "ERROR: Failed to update __version__ in $VERSION_FILE"
    exit 1
fi
echo "  Updated __version__ to $new_version"

# Commit only the version file, leaving anything else staged untouched
git commit -m "Update version to $new_version" -- "$VERSION_FILE"
echo "  Committed changes to git"

# Push, setting the upstream if the branch doesn't have one yet
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" &>/dev/null; then
    git push
else
    git push -u origin "$current_branch"
fi
echo "  Pushed $current_branch to GitHub"

# Summary
echo "========================================="
echo "Version update complete!"
echo "Branch:      $current_branch"
echo "New version: $new_version"
echo "========================================="
