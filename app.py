import os
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPES = " ".join([
    "user-top-read",
    "user-read-recently-played",
    "user-library-read",
    "playlist-read-private",
])

st.set_page_config(
    page_title="My Spotify Wrapped",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif;
        }
        .spotify-green { color: #1DB954; }
        .big-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1DB954;
        }
        .stat-label {
            font-size: 0.85rem;
            color: #b3b3b3;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        [data-testid="stSidebar"] {
            background-color: #121212;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)


def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SCOPES,
        cache_path=".cache",
        open_browser=True,
    ))


if "sp" not in st.session_state:
    st.session_state.sp = get_spotify_client()

sp = st.session_state.sp


@st.cache_data(ttl=3600)
def fetch_profile():
    return sp.current_user()


# ── Page content ──────────────────────────────────────────────────────────────

st.title("🎵 My Spotify Wrapped")
st.caption("A deeper look at your music — beyond what Spotify shows you.")

st.divider()

try:
    user = fetch_profile()

    col_avatar, col_info = st.columns([1, 4], gap="large")

    with col_avatar:
        if user.get("images"):
            st.image(user["images"][0]["url"], width=140)
        else:
            st.markdown("## 👤")

    with col_info:
        st.markdown(f"## {user['display_name']}")
        st.markdown(f"[Open Spotify Profile]({user['external_urls']['spotify']})")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"<div class='big-number'>{user['followers']['total']:,}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Followers</div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='big-number'>{user.get('country', '—')}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Country</div>", unsafe_allow_html=True)
        with m3:
            plan = user.get("product", "—").capitalize()
            st.markdown(f"<div class='big-number'>{plan}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Plan</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Navigate")
    st.markdown("""
    Use the **sidebar** to explore your stats:

    | Page | What you'll find |
    |------|-----------------|
    | 📊 Top Charts | Your top artists, tracks, and genres across different time ranges |
    | 🎵 Audio Features | The sonic fingerprint of your taste — energy, mood, danceability |
    | 🕐 Listening Patterns | When and how you listen, discovery rate, library timeline |
    | 🎧 Playlist Analysis | Mood maps, diversity scores, and track breakdowns per playlist |
    """)

except Exception as e:
    st.error(f"Could not connect to Spotify: {e}")
    st.info("Make sure your `.env` file has valid `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI`.")
