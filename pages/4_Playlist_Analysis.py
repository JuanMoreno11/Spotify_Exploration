import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import spotipy

st.set_page_config(page_title="Playlist Analysis", page_icon="🎧", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
        [data-testid="stSidebar"] { background-color: #121212; }
        .big-number { font-size: 2.2rem; font-weight: 700; color: #1DB954; }
        .stat-label { font-size: 0.8rem; color: #b3b3b3; text-transform: uppercase; letter-spacing: 0.08em; }
    </style>
""", unsafe_allow_html=True)

if "sp" not in st.session_state:
    st.error("Not connected to Spotify. Please go back to the Home page first.")
    st.stop()

sp = st.session_state.sp

SPOTIFY_GREEN = "#1DB954"
CHART_TEMPLATE = "plotly_dark"
AUDIO_FEATURES = ["danceability", "energy", "valence", "acousticness", "instrumentalness", "speechiness"]


@st.cache_data(ttl=3600)
def fetch_playlists():
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        for p in results["items"]:
            if p and p.get("tracks", {}).get("total", 0) > 0:
                playlists.append({
                    "id": p["id"],
                    "name": p["name"],
                    "total_tracks": p["tracks"]["total"],
                    "image_url": p["images"][0]["url"] if p.get("images") else None,
                    "owner": p["owner"]["display_name"],
                })
        results = sp.next(results) if results["next"] else None
    return playlists


@st.cache_data(ttl=3600)
def fetch_playlist_tracks(playlist_id: str):
    tracks = []
    results = sp.playlist_tracks(playlist_id, limit=100)
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(track)
        results = sp.next(results) if results["next"] else None
    return tracks


@st.cache_data(ttl=3600)
def build_playlist_df(playlist_id: str):
    tracks = fetch_playlist_tracks(playlist_id)
    if not tracks:
        return pd.DataFrame()

    ids = [t["id"] for t in tracks]
    features = []
    has_audio = True
    try:
        for i in range(0, len(ids), 100):
            batch = sp.audio_features(ids[i:i+100])
            if batch:
                features.extend([f for f in batch if f])
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 403:
            has_audio = False
        else:
            raise

    feat_map = {f["id"]: f for f in features}

    rows = []
    for track in tracks:
        row = {
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "popularity": track["popularity"],
            "duration_min": round(track["duration_ms"] / 60000, 2),
            "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify_url": track["external_urls"]["spotify"],
        }
        if has_audio:
            feat = feat_map.get(track["id"])
            if feat:
                row.update({k: feat[k] for k in AUDIO_FEATURES})
                row["tempo"] = feat["tempo"]
                row["loudness"] = feat["loudness"]
        rows.append(row)
    return pd.DataFrame(rows)


def diversity_score(df: pd.DataFrame) -> float:
    """0–100 score based on std deviation across audio features."""
    if df.empty or len(df) < 2:
        return 0.0
    stds = df[AUDIO_FEATURES].std()
    return round(float(stds.mean()) * 200, 1)  # scale to ~0-100


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🎧 Playlist Analysis")
st.caption("Explore the mood, energy, and diversity of your playlists.")

st.divider()

with st.spinner("Loading your playlists..."):
    playlists = fetch_playlists()

if not playlists:
    st.warning("No playlists found.")
    st.stop()

# Playlist picker
playlist_options = {p["name"]: p for p in playlists}
selected_name = st.selectbox(
    "Choose a playlist",
    options=list(playlist_options.keys()),
    format_func=lambda x: f"{x}  ({playlist_options[x]['total_tracks']} tracks)",
)
selected = playlist_options[selected_name]

col_img, col_meta = st.columns([1, 5], gap="large")
with col_img:
    if selected["image_url"]:
        st.image(selected["image_url"], width=110)
with col_meta:
    st.markdown(f"## {selected['name']}")
    st.caption(f"By {selected['owner']}  ·  {selected['total_tracks']} tracks")

st.divider()

with st.spinner("Fetching tracks and audio features..."):
    df = build_playlist_df(selected["id"])

if df.empty:
    st.warning("No track data available for this playlist.")
    st.stop()

has_audio = all(col in df.columns for col in AUDIO_FEATURES)

if not has_audio:
    st.info(
        "**Audio features unavailable.** Spotify deprecated the `/audio-features` endpoint "
        "for apps created after November 27, 2024. Mood map and sonic profile are hidden."
    )

# ── Summary Stats ─────────────────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<div class='big-number'>{len(df)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Tracks analysed</div>", unsafe_allow_html=True)
with m2:
    st.markdown(f"<div class='big-number'>{df['artist'].nunique()}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Unique artists</div>", unsafe_allow_html=True)
with m3:
    total_h = int(df["duration_min"].sum() // 60)
    total_m = int(df["duration_min"].sum() % 60)
    st.markdown(f"<div class='big-number'>{total_h}h {total_m}m</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Total duration</div>", unsafe_allow_html=True)
with m4:
    if has_audio:
        score = diversity_score(df)
        st.markdown(f"<div class='big-number'>{score}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Diversity score (0–100)</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='big-number'>{df['popularity'].mean():.0f}</div>", unsafe_allow_html=True)
        st.markdown("<div class='stat-label'>Avg popularity</div>", unsafe_allow_html=True)

st.divider()

# ── Mood Map ──────────────────────────────────────────────────────────────────

if has_audio:
    st.subheader("😊 Mood Map")
    st.caption("Every track plotted by happiness (valence) and energy. Dot size = popularity.")

    fig_mood = px.scatter(
        df,
        x="valence",
        y="energy",
        hover_name="name",
        hover_data={"artist": True, "valence": ":.2f", "energy": ":.2f", "danceability": ":.2f"},
        color="danceability",
        color_continuous_scale=[[0, "#191414"], [1, SPOTIFY_GREEN]],
        size="popularity",
        size_max=22,
        template=CHART_TEMPLATE,
        labels={"valence": "Valence (sad → happy)", "energy": "Energy (calm → intense)"},
    )

    for x, y, label in [
        (0.12, 0.88, "Angry / Intense"),
        (0.75, 0.88, "Happy / Energetic"),
        (0.12, 0.12, "Sad / Calm"),
        (0.75, 0.12, "Peaceful / Content"),
    ]:
        fig_mood.add_annotation(x=x, y=y, text=label, showarrow=False,
                                 font=dict(color="#535353", size=11))

    fig_mood.add_hline(y=0.5, line_dash="dot", line_color="#535353")
    fig_mood.add_vline(x=0.5, line_dash="dot", line_color="#535353")
    fig_mood.update_layout(height=460, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_mood, use_container_width=True)

    st.divider()

# ── Radar — Playlist Profile ──────────────────────────────────────────────────

if has_audio:
    st.subheader("🕸️ Playlist Sonic Profile")

    avg = df[AUDIO_FEATURES].mean()

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=avg.values.tolist() + [avg.values[0]],
        theta=AUDIO_FEATURES + [AUDIO_FEATURES[0]],
        fill="toself",
        fillcolor="rgba(29,185,84,0.2)",
        line=dict(color=SPOTIFY_GREEN, width=2),
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="#191414",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#535353", tickfont=dict(color="#b3b3b3")),
            angularaxis=dict(gridcolor="#535353", tickfont=dict(color="#ffffff", size=13)),
        ),
        template=CHART_TEMPLATE,
        showlegend=False,
        height=380,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

# ── Track List ────────────────────────────────────────────────────────────────

st.subheader("🎵 Track List")

search = st.text_input("Search tracks", placeholder="Filter by name or artist...")
display_df = df.copy()
if search:
    mask = (
        display_df["name"].str.contains(search, case=False, na=False) |
        display_df["artist"].str.contains(search, case=False, na=False)
    )
    display_df = display_df[mask]

for _, row in display_df.iterrows():
    c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
    with c1:
        if row["image_url"]:
            st.image(row["image_url"], width=48)
    with c2:
        st.markdown(f"**[{row['name']}]({row['spotify_url']})**")
        st.caption(row["artist"])
    with c3:
        if has_audio:
            st.caption(f"Energy: {row['energy']:.2f}  ·  Valence: {row['valence']:.2f}")
        else:
            st.caption(f"Popularity: {row['popularity']}")
    with c4:
        if has_audio:
            st.caption(f"Dance: {row['danceability']:.2f}  ·  {row['duration_min']:.1f} min")
        else:
            st.caption(f"{row['duration_min']:.1f} min")
