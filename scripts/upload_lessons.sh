#!/usr/bin/env bash
# Simulates the in-car boxes uploading lesson files, in the order they were uploaded in the field.
# Usage: ./scripts/upload_lessons.sh <bucket-name> [prefix] [delay-seconds]
set -euo pipefail
BUCKET="${1:?usage: upload_lessons.sh <bucket-name> [prefix] [delay-seconds]}"
PREFIX="${2:-incoming}"
DELAY="${3:-5}"
cd "$(dirname "$0")/.."
while read -r f; do
  [ -z "$f" ] && continue
  key="${PREFIX}/${f#sample_data/lessons/}"
  echo "uploading $f -> s3://${BUCKET}/${key}"
  aws s3 cp "$f" "s3://${BUCKET}/${key}" --only-show-errors
  sleep "$DELAY"
done < scripts/upload_order.txt
echo "done"
