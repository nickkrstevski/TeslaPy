#!/usr/bin/env bash
set -Eeuo pipefail

# Generate an EC P-256 key pair for Tesla Fleet API and place the public key
# at public_site/.well-known/appspecific/com.tesla.3p.public-key.pem

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KEYS_DIR="$ROOT_DIR/keys"
SITE_DIR="$ROOT_DIR/public_site"
WELL_KNOWN_DIR="$SITE_DIR/.well-known/appspecific"

mkdir -p "$KEYS_DIR" "$WELL_KNOWN_DIR"

PRIVATE_KEY_PATH="$KEYS_DIR/private-key.pem"
PUBLIC_KEY_PATH_TMP="$KEYS_DIR/public-key.pem"
PUBLIC_KEY_DEST="$WELL_KNOWN_DIR/com.tesla.3p.public-key.pem"

if command -v openssl >/dev/null 2>&1; then
  :
else
  echo "Error: openssl not found on PATH. Install via Homebrew: brew install openssl" >&2
  exit 1
fi

echo "Generating EC P-256 private key..."
openssl ecparam -name prime256v1 -genkey -noout -out "$PRIVATE_KEY_PATH"

echo "Deriving public key..."
openssl ec -in "$PRIVATE_KEY_PATH" -pubout -out "$PUBLIC_KEY_PATH_TMP"

echo "Placing public key at $PUBLIC_KEY_DEST"
cp "$PUBLIC_KEY_PATH_TMP" "$PUBLIC_KEY_DEST"

echo
echo "Done. Files:"
echo "  Private key: $PRIVATE_KEY_PATH"
echo "  Public key:  $PUBLIC_KEY_DEST"
echo
echo "Next steps:"
echo "  1) Deploy the contents of public_site/ to a site served at your domain root."
echo "     The public key must be reachable at: https://YOUR_DOMAIN/.well-known/appspecific/com.tesla.3p.public-key.pem"
echo "  2) Use https://YOUR_DOMAIN as an Allowed Origin URL in Tesla Developer Portal."
echo "  3) Use https://YOUR_DOMAIN/oauth/callback as an Allowed Redirect URI."
echo

