# Spotify Exploration — CLAUDE.md

Personal Spotify Wrapped dashboard built with Streamlit and the Spotify Web API (via spotipy).

## Tech stack

- **Python 3.11** (see `.python-version`)
- **Package manager**: `uv` — use `uv run` or activate `.venv`
- **Dependencies**: defined in `pyproject.toml`
- **Run the app**: `uv run streamlit run app.py`

## Project structure

```
app.py                      # Home page — auth, profile, navigation
main.py                     # Alternate entry point (unused/legacy)
pages/
  1_Top_Charts.py           # Top artists, tracks, genre breakdown
  2_Audio_Features.py       # Sonic profile, mood quadrant, feature distributions (503 fallback active)
  3_Listening_Patterns.py   # Heatmap, recently played feed, library timeline
  4_Playlist_Analysis.py    # Mood map, radar, track list per playlist (403 fallback active)
pyproject.toml              # Project metadata and dependencies
uv.lock                     # Locked dependency versions
.env                        # Secrets (gitignored) — copy from .env.example and fill in values
.env.example                # Committed template showing required env vars (no real values)
.cache                      # spotipy OAuth token cache (gitignored)
.cache-*                    # spotipy token variants (gitignored)
```

## Environment variables

`.env` is gitignored and never committed. Copy `.env.example` to `.env` and fill in real values:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

Obtain credentials at [developer.spotify.com](https://developer.spotify.com/dashboard). The redirect URI must be registered in the app settings there. `python-dotenv` loads this file automatically on every `streamlit run` — no manual sourcing needed.

## OAuth scopes

Defined in `app.py`:

- `user-top-read` — top artists and tracks
- `user-read-recently-played` — recently played feed
- `user-library-read` — saved/liked tracks
- `playlist-read-private` — user playlists

## Spotify API deprecations (November 2024)

**`/audio-features` is deprecated for apps created after November 27, 2024 — it returns HTTP 403.**

Both affected pages import `spotipy` directly and catch `SpotifyException` with `http_status == 403`:

- **Page 2 (Audio Features)**: `fetch_tracks_with_features()` returns an empty DataFrame on 403; the page shows a deprecation notice and stops
- **Page 4 (Playlist Analysis)**: `build_playlist_df()` sets `has_audio = False` on 403, builds rows without audio feature columns, and the page conditionally skips the mood map, radar chart, and diversity score — the track list and basic stats still render

When Spotify restores access (or if using a pre-November-2024 app), both pages will work as designed with no code changes needed.

## Security — credential hygiene

- `.env` and `.cache-*` are gitignored; real credentials must never be committed
- A legacy `.cache-` token file (containing a spotipy refresh token) was committed in early history and has been **fully scrubbed** using `git filter-repo --path .cache- --invert-paths` followed by a force-push
- If you ever suspect a token leak: regenerate the client secret in the Spotify Developer Dashboard — this immediately invalidates all existing refresh tokens for that app

## Streamlit patterns

- The Spotify client is initialized once in `app.py` and stored in `st.session_state.sp`
- All pages read from `st.session_state.sp`; if missing, they show an error and call `st.stop()`
- Data fetches are wrapped in `@st.cache_data(ttl=3600)` (1800s for recently played)
- Theme: dark (`#121212` sidebar, `#1DB954` Spotify green, `plotly_dark` chart template), Montserrat font

## Common commands

```bash
# Install dependencies
uv sync

# Run the app
uv run streamlit run app.py

# Add a dependency
uv add <package>

# If git remote is ever missing (e.g. after git filter-repo):
git remote add origin https://github.com/JuanMoreno11/Spotify_Exploration.git
git push --force origin master
```
