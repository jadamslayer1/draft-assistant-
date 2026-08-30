import time

import requests

BASE_URL = "https://api.sleeper.app/v1"

HEADERS = {
    "User-Agent": "FantasyDraftAssistant/1.0"
}

# Holds the specific reason the most recent request failed, so the
# UI can show the person what actually went wrong instead of just
# "couldn't reach Sleeper."
LAST_ERROR = None


# -----------------------------
# SAFE GET
# -----------------------------
def safe_get(url, max_attempts=4, backoff_seconds=1.5):
    """
    GET a URL with automatic retries on transient failures
    (timeouts, connection errors, rate limits) so a single
    refresh click doesn't fail just because one attempt hit
    a hiccup.
    """
    global LAST_ERROR
    LAST_ERROR = None

    for attempt in range(max_attempts):
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            if r.status_code == 429:
                # Rate limited — honor Retry-After if Sleeper sends
                # one, otherwise fall back to our own backoff.
                wait = float(
                    r.headers.get(
                        "Retry-After",
                        backoff_seconds * (attempt + 1)
                    )
                )
                LAST_ERROR = f"Rate limited by Sleeper (HTTP 429)"
                time.sleep(wait)
                continue

            r.raise_for_status()

            return r.json()

        except Exception as e:
            LAST_ERROR = f"{type(e).__name__}: {e}"

            if attempt < max_attempts - 1:
                time.sleep(backoff_seconds * (attempt + 1))

    print(f"Sleeper API Error after {max_attempts} attempts: {LAST_ERROR}")
    return None


# -----------------------------
# GET ACTIVE DRAFT FROM LEAGUE
# -----------------------------
def get_draft_from_league(league_id):

    if not league_id:
        return None

    url = f"{BASE_URL}/league/{league_id}/drafts"

    drafts = safe_get(url)

    if not drafts:
        return None

    if len(drafts) == 0:
        return None

    return drafts[0]["draft_id"]


# -----------------------------
# MANUAL DRAFT ID
# -----------------------------
def get_draft_by_id(draft_id):

    if not draft_id:
        return None

    return draft_id.strip()


# -----------------------------
# GET PICKS
# -----------------------------
def get_picks(draft_id):

    if not draft_id:
        return []

    url = f"{BASE_URL}/draft/{draft_id}/picks"

    picks = safe_get(url)

    # safe_get returns None specifically on a failed request (timeout,
    # bad draft_id, rate limit, etc). Keep that distinct from a
    # genuinely empty picks list, so the caller can tell "the draft
    # has no picks yet" apart from "the fetch failed."
    if picks is None:
        return None

    return picks


# -----------------------------
# CONVERT PICKS TO PLAYER NAMES
# -----------------------------
def drafted_player_names(picks):

    players = []

    for pick in picks:

        try:

            first = pick["metadata"]["first_name"]
            last = pick["metadata"]["last_name"]

            players.append(f"{first} {last}")

        except Exception:
            continue

    return players