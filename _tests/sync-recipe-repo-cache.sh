#!/usr/bin/env bash
set -uo pipefail

# Sync this repo's AutoPkg cache in ~/Library/AutoPkg/RecipeRepos to the branch
# checked out in this working copy, so autopkg runs test the pushed changes.
#
# The cache is found by matching its origin remote to this repo's origin
# remote, then switched to the same branch and updated from GitHub. Push your
# changes first: the cache can only pick up what is on GitHub.
#
# Usage: _tests/sync-recipe-repo-cache.sh [recipe-repos-dir]

repos_dir="${1:-$HOME/Library/AutoPkg/RecipeRepos}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! work_dir=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null); then
    echo "ERROR: $script_dir is not in a git repo" >&2
    exit 1
fi

# Reduce a remote URL to host/owner/repo, so that SSH and HTTPS forms match.
normalize_url() {
    local url="$1"
    url="${url%/}"
    url="${url%.git}"
    url="${url#*://}"      # drop scheme
    url="${url#*@}"        # drop user@
    url="${url/://}"       # git@host:owner/repo -> host/owner/repo
    echo "$url" | tr '[:upper:]' '[:lower:]'
}

if ! work_url=$(git -C "$work_dir" remote get-url origin 2>/dev/null); then
    echo "ERROR: $work_dir has no origin remote" >&2
    exit 1
fi
work_id=$(normalize_url "$work_url")

branch=$(git -C "$work_dir" rev-parse --abbrev-ref HEAD)
if [ "$branch" = "HEAD" ]; then
    echo "ERROR: $work_dir is on a detached HEAD. Check out a branch first." >&2
    exit 1
fi

# Find the cache with the same origin
cache=""
for repo in "$repos_dir"/*/; do
    repo="${repo%/}"
    url=$(git -C "$repo" remote get-url origin 2>/dev/null) || continue
    if [ "$(normalize_url "$url")" = "$work_id" ]; then
        cache="$repo"
        break
    fi
done
if [ -z "$cache" ]; then
    echo "ERROR: no repo in $repos_dir has origin $work_url" >&2
    echo "Add it first with: autopkg repo-add $work_url" >&2
    exit 1
fi

echo "Working copy: $work_dir"
echo "Cache:        $cache"
echo "Branch:       $branch"
echo ""

# The branch must be on GitHub for the cache to get it
if ! remote_sha=$(git -C "$work_dir" ls-remote --exit-code --heads origin "$branch" | cut -f1); then
    echo "ERROR: branch '$branch' is not on GitHub. Push it first:" >&2
    echo "  git push -u origin $branch" >&2
    exit 1
fi
if [ "$(git -C "$work_dir" rev-parse HEAD)" != "$remote_sha" ]; then
    echo "WARNING: the working copy's HEAD differs from origin/$branch."
    echo "  Unpushed commits won't be in the cache; push them first if you need them."
    echo ""
fi

if [ -n "$(git -C "$cache" status --porcelain --untracked-files=no)" ]; then
    echo "ERROR: the cache has uncommitted changes:" >&2
    git -C "$cache" status --short --untracked-files=no >&2
    exit 1
fi

if ! git -C "$cache" fetch --prune origin; then
    echo "ERROR: fetch failed in $cache" >&2
    exit 1
fi

# Switch branch, creating a local tracking branch if needed
if [ "$(git -C "$cache" rev-parse --abbrev-ref HEAD)" != "$branch" ]; then
    if git -C "$cache" show-ref --verify --quiet "refs/heads/$branch"; then
        git -C "$cache" checkout "$branch" || exit 1
    else
        git -C "$cache" checkout -b "$branch" --track "origin/$branch" || exit 1
    fi
fi

# Bring the cache up to date with origin/<branch>
if git -C "$cache" merge --ff-only "origin/$branch" >/dev/null 2>&1; then
    :
else
    # The branch has been rewritten on GitHub (e.g. after a force-push), so a
    # fast-forward isn't possible
    echo ""
    echo "The cache's '$branch' has diverged from origin/$branch (force-pushed?)."
    echo "Commits in the cache that are not on origin/$branch:"
    git -C "$cache" log --oneline "origin/$branch..HEAD"
    read -r -p "Reset the cache to origin/$branch, discarding those commits? [y/n] " answer
    if [[ "$answer" != [Yy] ]]; then
        echo "Not reset. The cache is on '$branch' but not in sync." >&2
        exit 1
    fi
    git -C "$cache" reset --hard "origin/$branch" || exit 1
fi

echo ""
echo "Cache is on '$branch' at $(git -C "$cache" log -1 --format='%h %s')"
