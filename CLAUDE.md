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
  2_Audio_Features.py       # Sonic profile, mood quadrant, feature distributions
  3_Listening_Patterns.py   # Heatmap, recently played feed, library timeline
  4_Playlist_Analysis.py    # Mood map, radar, track list per playlist
pyproject.toml              # Project metadata and dependencies
uv.lock                     # Locked dependency versions
.env                        # Secrets (gitignored) — see Environment Variables below
.cache                      # spotipy OAuth token cache (gitignored)
```

## Environment variables

Create a `.env` file in the project root (never commit it):

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

Obtain credentials at [developer.spotify.com](https://developer.spotify.com/dashboard). The redirect URI must be registered in the app settings there.

## OAuth scopes

Defined in `app.py`:

- `user-top-read` — top artists and tracks
- `user-read-recently-played` — recently played feed
- `user-library-read` — saved/liked tracks
- `playlist-read-private` — user playlists

## Spotify API deprecations (November 2024)

**`/audio-features` is deprecated for apps created after November 27, 2024 — it returns HTTP 403.**

Affected pages handle this gracefully:
- **Page 2 (Audio Features)**: shows a deprecation notice and stops rendering
- **Page 4 (Playlist Analysis)**: skips mood map, radar chart, and diversity score; falls back to popularity/duration data in the track list

When Spotify restores access (or if using a pre-November-2024 app), these pages will work as designed.

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
```
