import re
import time

import requests

from .config import load_config, save_config


def fetch_developer_token() -> str:
    """
    Auto-extract Apple Music developer token from music.apple.com JS bundle.
    Caches in ~/.config/yt2apple/config.json for 24 hours.
    Raises RuntimeError if extraction fails.
    """
    config = load_config()

    # Check cache (24h TTL)
    cached = config.get("developer_token")
    cached_at = config.get("developer_token_cached_at", 0)
    if cached and (time.time() - cached_at) < 86400:
        return cached

    # Fetch from JS bundle
    token = _extract_token_from_bundle()

    config["developer_token"] = token
    config["developer_token_cached_at"] = time.time()
    save_config(config)
    return token


def _extract_token_from_bundle() -> str:
    """Extract JWT token from music.apple.com JavaScript bundle."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    # Step 1: Get main page and find JS bundle URL
    resp = requests.get("https://beta.music.apple.com", headers=headers, timeout=15)
    resp.raise_for_status()

    # Find JS bundle - try multiple patterns as Apple changes these
    js_patterns = [
        r'/assets/index-legacy-[^"\']+\.js',
        r'/assets/index-[^"\']+\.js',
        r'src="(/assets/[^"]+\.js)"',
    ]

    js_path = None
    for pattern in js_patterns:
        match = re.search(pattern, resp.text)
        if match:
            js_path = match.group(0).strip('"\'')
            break

    if not js_path:
        raise RuntimeError(
            "Could not find Apple Music JS bundle. Apple may have changed their site structure."
        )

    # Step 2: Fetch JS bundle and extract JWT
    js_url = (
        f"https://beta.music.apple.com{js_path}"
        if js_path.startswith("/")
        else js_path
    )
    js_resp = requests.get(js_url, headers=headers, timeout=15)
    js_resp.raise_for_status()

    # JWT tokens start with eyJ (base64 encoded {"...)
    token_match = re.search(
        r'eyJh[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', js_resp.text
    )
    if not token_match:
        raise RuntimeError(
            "Could not extract developer token from Apple Music JS bundle. "
            "Apple may have changed their token format."
        )

    return token_match.group(0)


def get_user_token() -> str:
    """Get stored media-user-token from config. Raises if not set."""
    config = load_config()
    token = config.get("media_user_token")
    if not token:
        raise RuntimeError(
            "Apple Music user token not configured.\n"
            "Run: yt2apple setup"
        )
    return token


def _auth_headers(developer_token: str, user_token: str) -> dict:
    return {
        "Authorization": f"Bearer {developer_token}",
        "Music-User-Token": user_token,
        "Content-Type": "application/json",
        "Origin": "https://music.apple.com",
    }


def search_song(
    title: str,
    artist: str | None,
    developer_token: str,
    user_token: str,
    storefront: str = "kr",
) -> str | None:
    """
    Search Apple Music catalog for a song.
    Returns catalog song ID (string) or None if not found.

    Strategy:
    1. Try "artist title" query (if artist provided)
    2. Fall back to "title" only query
    """
    headers = _auth_headers(developer_token, user_token)
    base_url = f"https://amp-api.music.apple.com/v1/catalog/{storefront}/search"

    queries = []
    if artist:
        queries.append(f"{artist} {title}")
    queries.append(title)

    for query in queries:
        try:
            resp = requests.get(
                base_url,
                headers=headers,
                params={"term": query, "types": "songs", "limit": 5},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            songs = data.get("results", {}).get("songs", {}).get("data", [])
            if songs:
                return songs[0]["id"]
        except requests.RequestException:
            continue

    return None


def create_playlist(
    name: str,
    song_ids: list[str],
    developer_token: str,
    user_token: str,
) -> str | None:
    """
    Create a new Apple Music library playlist with given song IDs.
    Returns playlist ID or None on failure.
    """
    headers = _auth_headers(developer_token, user_token)

    payload = {
        "attributes": {
            "name": name,
            "description": "Created by yt2apple",
        },
        "relationships": {
            "tracks": {
                "data": [{"id": sid, "type": "songs"} for sid in song_ids]
            }
        },
    }

    resp = requests.post(
        "https://amp-api.music.apple.com/v1/me/library/playlists",
        headers=headers,
        json=payload,
        timeout=15,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        playlists = data.get("data", [])
        if playlists:
            return playlists[0]["id"]

    return None
