import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

st.set_page_config(page_title="Listening Patterns", page_icon="🕐", layout="wide")

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

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data(ttl=1800)
def fetch_recently_played(limit: int = 50):
    results = sp.current_user_recently_played(limit=limit)
    rows = []
    for item in results["items"]:
        track = item["track"]
        played_at = datetime.fromisoformat(item["played_at"].replace("Z", "+00:00"))
        rows.append({
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "played_at": played_at,
            "hour": played_at.hour,
            "day": played_at.strftime("%A"),
            "day_num": played_at.weekday(),
            "date": played_at.date(),
            "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify_url": track["external_urls"]["spotify"],
            "duration_ms": track["duration_ms"],
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def fetch_saved_tracks_timeline(limit: int = 50):
    """Fetch recently saved tracks with added_at timestamps."""
    results = sp.current_user_saved_tracks(limit=limit)
    rows = []
    for item in results["items"]:
        track = item["track"]
        added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
        artists = sp.artists([a["id"] for a in track["artists"][:1]])
        genres = artists["artists"][0].get("genres", []) if artists["artists"] else []
        rows.append({
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "added_at": added_at,
            "date": added_at.date(),
            "month": added_at.strftime("%Y-%m"),
            "genres": genres,
        })
    return pd.DataFrame(rows)


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🕐 Listening Patterns")
st.caption("When you listen, what you discover, and how your library grew.")

st.divider()

recent_df = fetch_recently_played()

# ── Summary stats ─────────────────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<div class='big-number'>{len(recent_df)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Tracks in history</div>", unsafe_allow_html=True)
with m2:
    unique_artists = recent_df["artist"].nunique()
    st.markdown(f"<div class='big-number'>{unique_artists}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Unique artists</div>", unsafe_allow_html=True)
with m3:
    total_min = recent_df["duration_ms"].sum() // 60000
    st.markdown(f"<div class='big-number'>{total_min}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Minutes listened</div>", unsafe_allow_html=True)
with m4:
    unique_tracks = recent_df["name"].nunique()
    st.markdown(f"<div class='big-number'>{unique_tracks}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Unique tracks</div>", unsafe_allow_html=True)

st.divider()

# ── Hour / Day Heatmap ────────────────────────────────────────────────────────

st.subheader("🗓️ When Do You Listen?")
st.caption("Listening activity by hour of day and day of week.")

if not recent_df.empty:
    heat_data = (
        recent_df.groupby(["day_num", "hour"])
        .size()
        .reset_index(name="plays")
    )
    pivot = heat_data.pivot(index="day_num", columns="hour", values="plays").fillna(0)
    pivot.index = [DAYS[i] for i in pivot.index]
    # Fill missing hours
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=[[0, "#191414"], [0.3, "#1a4a28"], [1, SPOTIFY_GREEN]],
        template=CHART_TEMPLATE,
        labels={"x": "Hour of day", "y": "Day", "color": "Plays"},
        aspect="auto",
    )
    fig_heat.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_showscale=False,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(24)),
            ticktext=[f"{h:02d}:00" for h in range(24)],
            tickangle=-45,
        ),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # Peak hour callout
    peak_hour = int(recent_df["hour"].mode()[0])
    peak_day = recent_df["day"].mode()[0]
    st.info(f"🎧 Your peak listening time is around **{peak_hour:02d}:00** and you listen most on **{peak_day}s**.")

st.divider()

# ── Recently Played Feed ──────────────────────────────────────────────────────

st.subheader("⏱️ Recently Played")

show_n = st.slider("Show last N tracks", min_value=10, max_value=50, value=20, step=5)

for _, row in recent_df.head(show_n).iterrows():
    c1, c2, c3 = st.columns([1, 5, 2])
    with c1:
        if row["image_url"]:
            st.image(row["image_url"], width=48)
    with c2:
        st.markdown(f"**[{row['name']}]({row['spotify_url']})**")
        st.caption(row["artist"])
    with c3:
        st.caption(row["played_at"].strftime("%b %d, %H:%M"))

st.divider()

# ── Library Timeline ──────────────────────────────────────────────────────────

st.subheader("📚 Recently Saved to Library")
st.caption("Your last 50 liked songs and when you added them.")

try:
    saved_df = fetch_saved_tracks_timeline()

    if not saved_df.empty:
        daily = saved_df.groupby("date").size().reset_index(name="tracks_added")
        daily["date"] = pd.to_datetime(daily["date"])

        fig_timeline = px.bar(
            daily,
            x="date",
            y="tracks_added",
            template=CHART_TEMPLATE,
            color_discrete_sequence=[SPOTIFY_GREEN],
            labels={"date": "Date", "tracks_added": "Tracks Added"},
        )
        fig_timeline.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Discovery rate: unique artists in saved vs recently played
        saved_artists = set(saved_df["artist"].unique())
        recent_artists = set(recent_df["artist"].unique())
        new_artists = recent_artists - saved_artists
        discovery_pct = round(len(new_artists) / max(len(recent_artists), 1) * 100)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"<div class='big-number'>{len(new_artists)}</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>New artists discovered recently</div>", unsafe_allow_html=True)
        with col_d2:
            st.markdown(f"<div class='big-number'>{discovery_pct}%</div>", unsafe_allow_html=True)
            st.markdown("<div class='stat-label'>Of recent listening is new artists</div>", unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Could not load saved tracks timeline: {e}")
