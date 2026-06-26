#!/usr/bin/env python3
"""
One-time OAuth2 setup for Google Ads API.

Run this script ONCE on your local machine (not in Docker) to generate
a refresh token. The refresh token goes into .env and never expires
(unless you revoke it).

Prerequisites:
  1. Go to Google Cloud Console → APIs & Services → Credentials
  2. Create an "OAuth 2.0 Client ID" (Desktop app type)
  3. Download the JSON and note the client_id and client_secret
  4. Set them in .env as GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET

Usage:
  pip install google-auth-oauthlib
  python scripts/get_google_ads_refresh_token.py
"""

import os
import sys

# Try to load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET in .env first.")
    print()
    print("Steps:")
    print("  1. Go to: https://console.cloud.google.com/apis/credentials")
    print("  2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
    print("  3. Application type: 'Desktop app'")
    print("  4. Copy the Client ID and Client Secret into .env")
    sys.exit(1)

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

# Google Ads API scope
SCOPES = ["https://www.googleapis.com/auth/adwords"]

# Build the OAuth flow from client credentials
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

# This opens a browser window for consent
print("Opening browser for Google OAuth consent...")
print("Sign in with: hc707consultinggroup@gmail.com")
print()

credentials = flow.run_local_server(port=8080)

print("=" * 60)
print("SUCCESS! Add these to your .env file:")
print("=" * 60)
print()
print(f"GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")
print()
print("=" * 60)
print("This token does not expire. You only need to run this once.")
print("=" * 60)
