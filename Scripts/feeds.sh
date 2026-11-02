#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Achang233 <https://github.com/Achang233>

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

ADD_FEED "momo" "nikkinikki-org/OpenWrt-momo" "main"
ADD_FEED "nikki" "nikkinikki-org/OpenWrt-nikki" "main"

# main predates the libffi move from the packages feed to the core tree.
# Backport the complete core package from a fixed upstream revision.
if [ "$WRT_SOURCE" = "VIKINGYFY/immortalwrt" ] && [ "$WRT_BRANCH" = "main" ]; then
  set -euo pipefail
  test ! -e package/libs/libffi
  LIBFFI_REV=17d1ac0c34b3f7eefb407277d25f4b78591f44c8
  LIBFFI_TMP=$(mktemp -d)
  trap 'rm -rf "$LIBFFI_TMP"' EXIT
  git init -q "$LIBFFI_TMP"
  git -C "$LIBFFI_TMP" remote add origin https://github.com/VIKINGYFY/immortalwrt.git
  git -C "$LIBFFI_TMP" sparse-checkout set package/libs/libffi
  git -C "$LIBFFI_TMP" fetch --depth=1 --filter=blob:none origin "$LIBFFI_REV"
  git -C "$LIBFFI_TMP" checkout --detach FETCH_HEAD
  test "$(git -C "$LIBFFI_TMP" rev-parse HEAD)" = "$LIBFFI_REV"
  grep -Fq '$(eval $(call HostBuild))' "$LIBFFI_TMP/package/libs/libffi/Makefile"
  grep -Fq '$(eval $(call BuildPackage,libffi))' "$LIBFFI_TMP/package/libs/libffi/Makefile"
  mkdir -p package/libs
  cp -a "$LIBFFI_TMP/package/libs/libffi" package/libs/
  echo "Backported libffi from $LIBFFI_REV"
fi
