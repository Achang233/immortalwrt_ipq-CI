#!/bin/bash
# SPDX-License-Identifier: MIT
set -euo pipefail

REPORT_DIR="$GITHUB_WORKSPACE/build-reports"
mkdir -p "$REPORT_DIR"
date -u +%FT%TZ > "$REPORT_DIR/collected-at.txt"
cp /etc/os-release "$REPORT_DIR/os-release.txt"
df -h > "$REPORT_DIR/disk.txt"
git -C "$GITHUB_WORKSPACE" rev-parse HEAD > "$REPORT_DIR/ci-commit.txt"

# Initialization can fail before the source checkout exists.
if [ -d "$GITHUB_WORKSPACE/wrt/.git" ]; then
  cd "$GITHUB_WORKSPACE/wrt"
  git rev-parse HEAD > "$REPORT_DIR/source-commit.txt"
  for report in .config feeds.conf.default athena-build.json; do
    if [ -f "$report" ]; then
      cp "$report" "$REPORT_DIR/${report#.}"
    fi
  done
  if [ -d feeds ]; then
    for feed in feeds/*; do
      if [ -d "$feed/.git" ] || [ -f "$feed/.git" ]; then
        printf '%s ' "${feed##*/}"
        git -C "$feed" rev-parse HEAD
      fi
    done > "$REPORT_DIR/feeds-commits.txt"
  fi
  if [ -x staging_dir/host/bin/ccache ]; then
    CCACHE_DIR="$PWD/.ccache" staging_dir/host/bin/ccache -s > "$REPORT_DIR/ccache.txt"
  fi
  if [ -f scripts/build-time-report.pl ] && [ -f "$REPORT_DIR/parallel.tsv" ]; then
    perl scripts/build-time-report.pl -n 30 "$REPORT_DIR/parallel.tsv" > "$REPORT_DIR/parallel-report.txt"
  fi
fi
