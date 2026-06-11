#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
DEFAULT_SOURCE_LANGUAGE_ID="${SOURCE_LANGUAGE_ID:-21}"
DEFAULT_OUTPUT_FORMAT="${OUTPUT_FORMAT:-pdf}"
DEFAULT_DOWNLOAD_DIR="${DOWNLOAD_DIR:-$HOME/Downloads}"
DEFAULT_EMAIL="${EMAIL:-admin@curriculum.edu}"
DEFAULT_PASSWORD="${PASSWORD:-admin123}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

json_get() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data.get(sys.argv[1], "") or "")' "$1"
}

slugify() {
  python3 -c 'import re,sys; print(re.sub(r"[^A-Za-z0-9._-]+", "-", sys.argv[1]).strip("-") or "translation")' "$1"
}

abs_path() {
  python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$1"
}

need_cmd curl
need_cmd python3

printf 'API URL [%s]: ' "$API_URL"
read -r input_api_url
if [ -n "${input_api_url:-}" ]; then
  API_URL="${input_api_url%/}"
else
  API_URL="${API_URL%/}"
fi

printf 'Email [%s]: ' "$DEFAULT_EMAIL"
read -r EMAIL_INPUT
EMAIL="${EMAIL_INPUT:-$DEFAULT_EMAIL}"

if [ -n "${PASSWORD:-}" ]; then
  PASSWORD_VALUE="$PASSWORD"
else
  printf 'Password [default admin123, press Enter to use]: '
  read -rs PASSWORD_INPUT
  echo
  PASSWORD_VALUE="${PASSWORD_INPUT:-$DEFAULT_PASSWORD}"
fi

LOGIN_RESPONSE="$(curl -fsS \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"email":sys.argv[1],"password":sys.argv[2]}))' "$EMAIL" "$PASSWORD_VALUE")" \
  "$API_URL/auth/login")"

ACCESS_TOKEN="$(printf '%s' "$LOGIN_RESPONSE" | json_get access_token)"
if [ -z "$ACCESS_TOKEN" ]; then
  echo "Login failed: no access token returned." >&2
  exit 1
fi

echo
printf 'Book file path, e.g. ~/Downloads/book.docx: '
read -r BOOK_FILE_INPUT
BOOK_FILE="$(abs_path "$BOOK_FILE_INPUT")"
if [ ! -f "$BOOK_FILE" ]; then
  echo "File not found: $BOOK_FILE" >&2
  exit 1
fi

DEFAULT_TITLE="$(basename "$BOOK_FILE")"
printf 'Book title [%s]: ' "$DEFAULT_TITLE"
read -r TITLE_INPUT
TITLE="${TITLE_INPUT:-$DEFAULT_TITLE}"

printf 'Subject [optional]: '
read -r SUBJECT

printf 'First content page [1]: '
read -r FIRST_CONTENT_PAGE
FIRST_CONTENT_PAGE="${FIRST_CONTENT_PAGE:-1}"

echo
echo "Uploading book..."
UPLOAD_ARGS=(-fsS -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -F "file=@$BOOK_FILE" -F "title=$TITLE" -F "first_content_page=$FIRST_CONTENT_PAGE")
if [ -n "${SUBJECT:-}" ]; then
  UPLOAD_ARGS+=(-F "subject=$SUBJECT")
fi
UPLOAD_RESPONSE="$(curl "${UPLOAD_ARGS[@]}" "$API_URL/admin/books/upload")"
BOOK_ID="$(printf '%s' "$UPLOAD_RESPONSE" | json_get id)"
if [ -z "$BOOK_ID" ]; then
  echo "Upload failed. Response:" >&2
  echo "$UPLOAD_RESPONSE" >&2
  exit 1
fi

echo "Uploaded book ID: $BOOK_ID"

BOOK_STATUS="pending"
echo
echo "Waiting for extraction/normalization..."
for _ in $(seq 1 180); do
  BOOK_RESPONSE="$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "$API_URL/admin/content/books/$BOOK_ID")"
  BOOK_STATUS="$(printf '%s' "$BOOK_RESPONSE" | json_get extraction_status)"
  echo "Extraction status: ${BOOK_STATUS:-unknown}"
  if [ "$BOOK_STATUS" = "done" ]; then
    break
  fi
  if [ "$BOOK_STATUS" = "failed" ]; then
    echo "Book extraction failed." >&2
    exit 1
  fi
  sleep 5
done

if [ "$BOOK_STATUS" != "done" ]; then
  echo "Timed out waiting for extraction. Book ID: $BOOK_ID" >&2
  exit 1
fi

echo
echo "Available languages:"
LANGUAGES_RESPONSE="$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "$API_URL/admin/languages?limit=200" || true)"
if [ -n "$LANGUAGES_RESPONSE" ]; then
  python3 - "$LANGUAGES_RESPONSE" <<'PY'
import json, sys
try:
    langs = json.loads(sys.argv[1])
except Exception:
    langs = []
if isinstance(langs, list) and langs:
    for lang in langs:
        active = "" if lang.get("is_active", True) else " inactive"
        print(f'{lang.get("id")}: {lang.get("name")} ({lang.get("code")}) {lang.get("native_name") or ""}{active}')
else:
    print("Could not list languages from API. Enter the language ID manually.")
PY
else
  echo "Could not list languages from API. Enter the language ID manually."
fi

echo
printf 'Target language ID: '
read -r LANGUAGE_ID
if [ -z "$LANGUAGE_ID" ]; then
  echo "Target language ID is required." >&2
  exit 1
fi

printf 'Source language ID [%s]: ' "$DEFAULT_SOURCE_LANGUAGE_ID"
read -r SOURCE_LANGUAGE_ID
SOURCE_LANGUAGE_ID="${SOURCE_LANGUAGE_ID:-$DEFAULT_SOURCE_LANGUAGE_ID}"

printf 'Output format [%s]: ' "$DEFAULT_OUTPUT_FORMAT"
read -r OUTPUT_FORMAT
OUTPUT_FORMAT="${OUTPUT_FORMAT:-$DEFAULT_OUTPUT_FORMAT}"

mkdir -p "$DEFAULT_DOWNLOAD_DIR"

echo
echo "Starting translation..."
START_URL="$API_URL/student/translate?content_type=book&content_id=$BOOK_ID&language_id=$LANGUAGE_ID&source_language_id=$SOURCE_LANGUAGE_ID&output_format=$OUTPUT_FORMAT"
START_RESPONSE="$(curl -fsS -X POST -H "Authorization: Bearer $ACCESS_TOKEN" "$START_URL")"
TRANSLATION_ID="$(printf '%s' "$START_RESPONSE" | json_get translation_id)"
TASK_ID="$(printf '%s' "$START_RESPONSE" | json_get task_id)"
STATUS="$(printf '%s' "$START_RESPONSE" | json_get status)"

if [ -z "$TRANSLATION_ID" ]; then
  echo "Could not start translation. Response:" >&2
  echo "$START_RESPONSE" >&2
  exit 1
fi

echo "Translation ID: $TRANSLATION_ID"
echo "Initial status: ${STATUS:-unknown}"
if [ -n "$TASK_ID" ]; then
  echo "Task ID: $TASK_ID"
fi

if [ "${STATUS:-}" != "done" ]; then
  echo
  echo "Polling until complete..."
  while true; do
    sleep 5
    if [ -n "$TASK_ID" ]; then
      STATUS_RESPONSE="$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "$API_URL/student/translate/status/$TASK_ID")"
      STATUS="$(printf '%s' "$STATUS_RESPONSE" | json_get status)"
      ERROR_MESSAGE="$(printf '%s' "$STATUS_RESPONSE" | json_get error_message)"
    else
      STATUS_RESPONSE="$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" "$API_URL/student/translate/$TRANSLATION_ID")"
      STATUS="$(printf '%s' "$STATUS_RESPONSE" | json_get status)"
      ERROR_MESSAGE=""
    fi

    echo "Status: ${STATUS:-unknown}"
    if [ "$STATUS" = "done" ]; then
      break
    fi
    if [ "$STATUS" = "failed" ]; then
      echo "Translation failed: $ERROR_MESSAGE" >&2
      exit 1
    fi
  done
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
FILE_BASE="$(slugify "${TITLE}-lang-${LANGUAGE_ID}-${TIMESTAMP}")"
OUTPUT_FILE="$DEFAULT_DOWNLOAD_DIR/${FILE_BASE}.${OUTPUT_FORMAT}"

echo
echo "Downloading to: $OUTPUT_FILE"
curl -fL \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_URL/translations/$TRANSLATION_ID/download?format=$OUTPUT_FORMAT&refresh_cache=true&cache_variant=script-$TIMESTAMP" \
  -o "$OUTPUT_FILE"

echo
echo "Done: $OUTPUT_FILE"
