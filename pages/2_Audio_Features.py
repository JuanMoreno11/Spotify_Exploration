import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import spotipy

st.set_page_config(page_title="Audio Features", page_icon="🎵", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
        [data-testid="stSidebar"] { background-color: #121212; }
    </style>
""", unsafe_allow_html=True)

if "sp" not in st.session_state:
    st.error("Not connected to Spotify. Please go back to the Home page first.")
    st.stop()

sp = st.session_state.sp

SPOTIFY_GREEN = "#1DB954"
CHART_TEMPLATE = "plotly_dark"

FEATURE_DESCRIPTIONS = {
    "danceability": "How suitable for dancing (rhythm, tempo, beat strength)",
    "energy": "Perceptual intensity and activity",
    "valence": "Musical positiveness — high = happy, low = sad/angry",
    "acousticness": "Confidence the track is acoustic",
    "instrumentalness": "Predicts whether a track has no vocals",
    "speechiness": "Presence of spoken words",
    "liveness": "Detects presence of a live audience",
}

RADAR_FEATURES = ["danceability", "energy", "valence", "acousticness", "instrumentalness", "speechiness"]

TIME_RANGES = {
    "Last 4 weeks": "short_term",
    "Last 6 months": "medium_term",
    "All time": "long_term",
}


@st.cache_data(ttl=3600)
def fetch_tracks_with_features(time_range: str, limit: int = 50):
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    tracks = results["items"]
    if not tracks:
        return pd.DataFrame()

    ids = [t["id"] for t in tracks]
    # Fetch in batches of 100 (API limit)
    features = []
    try:
        for i in range(0, len(ids), 100):
            batch = sp.audio_features(ids[i:i+100])
            if batch:
                features.extend([f for f in batch if f])
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 403:
            return pd.DataFrame()
        raise

    feature_map = {f["id"]: f for f in features}

    rows = []
    for track in tracks:
        feat = feature_map.get(track["id"])
        if not feat:
            continue
        rows.append({
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "popularity": track["popularity"],
            "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify_url": track["external_urls"]["spotify"],
            **{k: feat[k] for k in RADAR_FEATURES},
            "tempo": feat["tempo"],
            "loudness": feat["loudness"],
            "duration_min": round(track["duration_ms"] / 60000, 2),
        })
    return pd.DataFrame(rows)


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🎵 Audio Features")
st.caption("The sonic fingerprint of your taste.")

time_label = st.radio("Time range", list(TIME_RANGES.keys()), horizontal=True, index=1)
time_range = TIME_RANGES[time_label]

df = fetch_tracks_with_features(time_range)

if df.empty:
    st.warning(
        "**Audio Features unavailable.** Spotify deprecated the `/audio-features` endpoint "
        "for apps created after November 27, 2024, returning HTTP 403. "
        "This page cannot be displayed until Spotify restores access."
    )
    st.stop()

st.divider()

# ── Radar — Average Profile ───────────────────────────────────────────────────

st.subheader("🕸️ Your Sonic Profile")
st.caption("Average audio features across your top tracks.")

avg = df[RADAR_FEATURES].mean()

fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=avg.values.tolist() + [avg.values[0]],
    theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
    fill="toself",
    fillcolor="rgba(29,185,84,0.2)",
    line=dict(color=SPOTIFY_GREEN, width=2),
    name="Your profile",
))
fig_radar.update_layout(
    polar=dict(
        bgcolor="#191414",
        radialaxis=dict(visible=True, range=[0, 1], gridcolor="#535353", tickfont=dict(color="#b3b3b3")),
        angularaxis=dict(gridcolor="#535353", tickfont=dict(color="#ffffff", size=13)),
    ),
    template=CHART_TEMPLATE,
    showlegend=False,
    height=420,
    margin=dict(l=60, r=60, t=40, b=40),
)
st.plotly_chart(fig_radar, use_container_width=True)

with st.expander("What do these features mean?"):
    for feat, desc in FEATURE_DESCRIPTIONS.items():
        st.markdown(f"**{feat.capitalize()}** — {desc}")

st.divider()

# ── Mood Quadrant ─────────────────────────────────────────────────────────────

st.subheader("😊 Mood Quadrant")
st.caption("Valence (happiness) vs Energy. Each dot is one of your top tracks.")

fig_mood = px.scatter(
    df,
    x="valence",
    y="energy",
    hover_name="name",
    hover_data={"artist": True, "valence": ":.2f", "energy": ":.2f"},
    color="danceability",
    color_continuous_scale=[[0, "#191414"], [1, SPOTIFY_GREEN]],
    size="popularity",
    size_max=20,
    template=CHART_TEMPLATE,
    labels={"valence": "Valence (sad → happy)", "energy": "Energy (calm → intense)"},
)

# Quadrant labels
for x, y, label in [
    (0.15, 0.85, "Angry / Intense"),
    (0.75, 0.85, "Happy / Energetic"),
    (0.15, 0.15, "Sad / Calm"),
    (0.75, 0.15, "Peaceful / Content"),
]:
    fig_mood.add_annotation(x=x, y=y, text=label, showarrow=False,
                             font=dict(color="#535353", size=11))

fig_mood.add_hline(y=0.5, line_dash="dot", line_color="#535353")
fig_mood.add_vline(x=0.5, line_dash="dot", line_color="#535353")
fig_mood.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig_mood, use_container_width=True)

st.divider()

# ── Feature Distributions ─────────────────────────────────────────────────────

st.subheader("📊 Feature Distributions")
st.caption("How your top tracks are spread across each audio feature.")

cols = st.columns(3)
for i, feat in enumerate(RADAR_FEATURES):
    with cols[i % 3]:
        fig_hist = px.histogram(
            df,
            x=feat,
            nbins=15,
            template=CHART_TEMPLATE,
            color_discrete_sequence=[SPOTIFY_GREEN],
            labels={feat: feat.capitalize()},
        )
        fig_hist.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            height=200,
            title=dict(text=feat.capitalize(), font=dict(size=13)),
            bargap=0.05,
        )
        fig_hist.update_xaxes(range=[0, 1])
        st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ── Tempo & Loudness ──────────────────────────────────────────────────────────

st.subheader("🥁 Tempo & Loudness")

col_t, col_l = st.columns(2, gap="large")

with col_t:
    fig_tempo = px.histogram(
        df, x="tempo", nbins=20,
        template=CHART_TEMPLATE,
        color_discrete_sequence=[SPOTIFY_GREEN],
        labels={"tempo": "BPM"},
        title="Tempo Distribution (BPM)",
    )
    fig_tempo.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0), height=280)
    st.plotly_chart(fig_tempo, use_container_width=True)
    st.caption(f"Average tempo: **{df['tempo'].mean():.0f} BPM**")

with col_l:
    fig_loud = px.histogram(
        df, x="loudness", nbins=20,
        template=CHART_TEMPLATE,
        color_discrete_sequence=[SPOTIFY_GREEN],
        labels={"loudness": "Loudness (dB)"},
        title="Loudness Distribution (dB)",
    )
    fig_loud.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0), height=280)
    st.plotly_chart(fig_loud, use_container_width=True)
    st.caption(f"Average loudness: **{df['loudness'].mean():.1f} dB**")
