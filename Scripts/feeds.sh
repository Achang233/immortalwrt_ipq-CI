#!/bin/bash

# Feeds.sh
# Set up feeds directly in the shell script

# Ensure we are in the OpenWrt source root or can find feeds.conf.default
if [ -f "feeds.conf.default" ]; then
  FEEDS_CONF="feeds.conf.default"
else
  echo "feeds.conf.default not found!"
  exit 1
fi

# Backup
cp -a "$FEEDS_CONF" "$FEEDS_CONF.bak.$(date +%s)"
echo "Backup created: $FEEDS_CONF.bak.*"

ADD_FEED() {
  local NAME=$1
  local REPO=$2
  local BRANCH=$3
  local TYPE=$4
  local ENTRY

  # Validation
  if [ -z "$NAME" ] || [ -z "$REPO" ]; then
    echo "Usage: ADD_FEED <name> <repo> [branch] [type]"
    return
  fi

  # Normalize GitHub shortcut owner/repo -> https://github.com/owner/repo.git
  if [[ "$REPO" != *":"* && "$REPO" != "http"* && "$REPO" != "https"* && "$REPO" != *".git" && "$REPO" == *"/"* && $(echo "$REPO" | grep -E "^[^./]+/[^./]+$") ]]; then
    REPO="https://github.com/$REPO.git"
  fi

  # Determine entry format
  if [ "$TYPE" = "svn" ]; then
    ENTRY="src-svn $NAME $REPO"
  else
    if [ -n "$BRANCH" ]; then
      ENTRY="src-git $NAME $REPO;$BRANCH"
    else
      ENTRY="src-git $NAME $REPO"
    fi
  fi

  # Remove existing entry with the same name
  # Uses sed -E for extended regex support
  # Matches start of line, optional whitespace, src-xxx, whitespace, NAME, word boundary
  sed -E -i "/^[[:space:]]*src-[^[:space:]]+[[:space:]]+${NAME}\b/d" "$FEEDS_CONF" || true

  # Add new entry
  echo "Add feed: $ENTRY"
  echo "$ENTRY" >> "$FEEDS_CONF"
}

# Add feeds here
# ADD_FEED "name" "repo" "branch" "type"

# Example:
# ADD_FEED "helloworld" "fw876/helloworld"
# ADD_FEED "custompkg" "https://github.com/username/custom-feeds.git" "main"
# ADD_FEED "customsvn" "https://example.com/svn/feeds/custom" "" "svn"

# ADD_FEED "qmodem" "FUjr/QModem" "main"
ADD_FEED "momo" "nikkinikki-org/OpenWrt-momo" "main"
ADD_FEED "nikki" "nikkinikki-org/OpenWrt-nikki" "main"