#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$repo_root/dist/client"

rm -rf "$output_dir"
mkdir -p "$output_dir"
cp -R "$repo_root/site/." "$output_dir/"

printf 'Built BoundaryBench site into %s\n' "$output_dir"
