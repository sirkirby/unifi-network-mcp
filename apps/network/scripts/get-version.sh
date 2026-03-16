#!/bin/bash
# Get PEP 440 compliant version from git tags
# Used by Makefile and CI workflows to ensure consistent versioning
#
# Git describe format: v0.3.2-1-g8b0ee79
#   - v0.3.2 = last tag
#   - 1 = commits since tag
#   - g8b0ee79 = commit hash
#
# PEP 440 format: 0.3.3.dev1
#   - 0.3.3 = next patch version
#   - .dev1 = 1 commit after last release

RAW=$(git describe --tags --always 2>/dev/null || echo "v0.0.0")
RAW=${RAW#v}  # Strip leading 'v'

if [[ "$RAW" == *-* ]]; then
    # Commits after tag: 0.3.2-1-gabc1234 -> 0.3.3.dev1
    BASE=$(echo "$RAW" | cut -d'-' -f1)
    COMMITS=$(echo "$RAW" | cut -d'-' -f2)

    MAJOR=$(echo "$BASE" | cut -d'.' -f1)
    MINOR=$(echo "$BASE" | cut -d'.' -f2)
    PATCH=$(echo "$BASE" | cut -d'.' -f3)

    NEWPATCH=$((PATCH + 1))
    VERSION="${MAJOR}.${MINOR}.${NEWPATCH}.dev${COMMITS}"
else
    # Exact tag match: 0.3.2
    VERSION="$RAW"
fi

echo "$VERSION"
