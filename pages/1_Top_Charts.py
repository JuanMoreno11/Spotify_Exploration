import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Top Charts", page_icon="📊", layout="wide")

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

TIME_RANGES = {
    "Last 4 weeks": "short_term",
    "Last 6 months": "medium_term",
    "All time": "long_term",
}


@st.cache_data(ttl=3600)
def fetch_top_artists(time_range: str, limit: int = 20):
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    rows = []
    for i, artist in enumerate(results["items"], 1):
        genres = artist.get("genres", [])
        rows.append({
            "rank": i,
            "name": artist["name"],
            "popularity": artist["popularity"],
            "followers": artist["followers"]["total"],
            "genres": genres,
            "primary_genre": genres[0] if genres else "Unknown",
            "image_url": artist["images"][0]["url"] if artist["images"] else None,
            "spotify_url": artist["external_urls"]["spotify"],
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def fetch_top_tracks(time_range: str, limit: int = 20):
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    rows = []
    for i, track in enumerate(results["items"], 1):
        rows.append({
            "rank": i,
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "popularity": track["popularity"],
            "duration_ms": track["duration_ms"],
            "duration_min": round(track["duration_ms"] / 60000, 2),
            "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify_url": track["external_urls"]["spotify"],
        })
    return pd.DataFrame(rows)


def genre_counts(artists_df: pd.DataFrame) -> pd.DataFrame:
    all_genres = [g for genres in artists_df["genres"] for g in genres]
    return (
        pd.Series(all_genres)
        .value_counts()
        .reset_index()
        .rename(columns={"index": "genre", 0: "count", "count": "count"})
        .head(15)
    )


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("📊 Top Charts")

time_label = st.radio(
    "Time range",
    options=list(TIME_RANGES.keys()),
    horizontal=True,
    index=1,
)
time_range = TIME_RANGES[time_label]

artists_df = fetch_top_artists(time_range)
tracks_df = fetch_top_tracks(time_range)

st.divider()

# ── Top Artists ───────────────────────────────────────────────────────────────

st.subheader("🎤 Top Artists")

col_chart, col_cards = st.columns([3, 2], gap="large")

with col_chart:
    fig = px.bar(
        artists_df,
        x="popularity",
        y="name",
        orientation="h",
        color="popularity",
        color_continuous_scale=[[0, "#191414"], [1, SPOTIFY_GREEN]],
        template=CHART_TEMPLATE,
        labels={"popularity": "Popularity Score", "name": ""},
        hover_data=["primary_genre", "followers"],
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_cards:
    st.markdown("**Your top 5**")
    for _, row in artists_df.head(5).iterrows():
        c1, c2 = st.columns([1, 3])
        with c1:
            if row["image_url"]:
                st.image(row["image_url"], width=56)
        with c2:
            st.markdown(f"**#{row['rank']} [{row['name']}]({row['spotify_url']})**")
            st.caption(row["primary_genre"].title() if row["primary_genre"] != "Unknown" else "")

st.divider()

# ── Top Tracks ────────────────────────────────────────────────────────────────

st.subheader("🎵 Top Tracks")

col_tchart, col_tcards = st.columns([3, 2], gap="large")

with col_tchart:
    fig2 = px.bar(
        tracks_df,
        x="popularity",
        y="name",
        orientation="h",
        color="popularity",
        color_continuous_scale=[[0, "#191414"], [1, SPOTIFY_GREEN]],
        template=CHART_TEMPLATE,
        labels={"popularity": "Popularity Score", "name": ""},
        hover_data=["artist", "album", "duration_min"],
    )
    fig2.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=500,
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_tcards:
    st.markdown("**Your top 5**")
    for _, row in tracks_df.head(5).iterrows():
        c1, c2 = st.columns([1, 3])
        with c1:
            if row["image_url"]:
                st.image(row["image_url"], width=56)
        with c2:
            st.markdown(f"**#{row['rank']} [{row['name']}]({row['spotify_url']})**")
            st.caption(row["artist"])

st.divider()

# ── Genre Breakdown ───────────────────────────────────────────────────────────

st.subheader("🎸 Genre Breakdown")

genres_df = genre_counts(artists_df)

col_pie, col_bar = st.columns(2, gap="large")

with col_pie:
    fig3 = px.pie(
        genres_df,
        names="genre" if "genre" in genres_df.columns else genres_df.columns[0],
        values="count",
        color_discrete_sequence=px.colors.sequential.Greens_r,
        template=CHART_TEMPLATE,
        hole=0.4,
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    fig3.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig3, use_container_width=True)

with col_bar:
    genre_col = genres_df.columns[0]
    fig4 = px.bar(
        genres_df,
        x="count",
        y=genre_col,
        orientation="h",
        color="count",
        color_continuous_scale=[[0, "#191414"], [1, SPOTIFY_GREEN]],
        template=CHART_TEMPLATE,
        labels={"count": "Artists", genre_col: ""},
    )
    fig4.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig4, use_container_width=True)
