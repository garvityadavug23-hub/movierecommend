import streamlit as st
import pandas as pd
import requests
import ast
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TMDB_API_KEY = "63c39d2a4b6cbbe2c300411d8980ade1"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

MOOD_GENRE_MAP = {
    "Happy":     ["Comedy", "Animation", "Family", "Music"],
    "Sad":       ["Drama", "Romance"],
    "Thrilling": ["Thriller", "Action", "Crime", "Mystery"],
    "Romantic":  ["Romance", "Drama"],
}

ERA_YEAR_MAP = {
    "2000s": (2000, 2009),
    "2010s": (2010, 2019),
    "2020s": (2020, 2030),
}

@st.cache_data
def load_data():
    df = pd.read_csv("tmdb_5000_movies.csv")
    return df

movies_raw = load_data()
movies_raw = movies_raw[['id', 'title', 'overview', 'genres', 'vote_average', 'release_date']].dropna()

def convert(obj):
    L = []
    try:
        for i in ast.literal_eval(obj):
            L.append(i['name'])
    except:
        pass
    return L

movies_raw['genre_list'] = movies_raw['genres'].apply(convert)
movies_raw['genres_str'] = movies_raw['genre_list'].apply(lambda x: " ".join(x))
movies_raw['tags'] = movies_raw['overview'] + " " + movies_raw['genres_str']

cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(movies_raw['tags']).toarray()
similarity = cosine_similarity(vectors)

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "selected_watch" not in st.session_state:
    st.session_state.selected_watch = None

st.set_page_config(layout="wide")
st.title("🎬 CineAI PRO")

col1, col2 = st.columns(2)
with col1:
    mood = st.selectbox("Mood (optional)", ["Any", "Happy", "Sad", "Thrilling", "Romantic"])
    genre = st.selectbox("Genre (optional)", ["Any", "Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Animation"])
with col2:
    era = st.selectbox("Era (optional)", ["Any", "2000s", "2010s", "2020s"])
    text = st.text_input("Describe what you want (optional)")

selected_movie = st.selectbox("Base Movie (for similarity)", movies_raw['title'].values)

def get_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        data = requests.get(url, timeout=5).json()
        if data.get("poster_path"):
            return f"{IMAGE_BASE}{data['poster_path']}"
    except:
        pass
    return "https://via.placeholder.com/300x450?text=No+Image"

def get_trailer(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        data = requests.get(url, timeout=5).json()
        for vid in data.get("results", []):
            if vid["type"] == "Trailer" and vid["site"] == "YouTube":
                return f"https://www.youtube.com/watch?v={vid['key']}"
    except:
        pass
    return None

def recommend(movie, mood_filter, genre_filter, era_filter, text_filter):
    idx_list = movies_raw[movies_raw['title'] == movie].index
    if len(idx_list) == 0:
        return []

    idx = idx_list[0]
    distances = sorted(list(enumerate(similarity[idx])), key=lambda x: x[1], reverse=True)[1:101]

    scored = []
    for i, base_score in distances:
        row = movies_raw.iloc[i]
        boost = 0

        if genre_filter != "Any":
            if genre_filter in row['genre_list']:
                boost += 0.3

        if mood_filter != "Any":
            mood_genres = MOOD_GENRE_MAP.get(mood_filter, [])
            if any(g in row['genre_list'] for g in mood_genres):
                boost += 0.3

        if era_filter != "Any":
            try:
                year = int(str(row['release_date'])[:4])
                start, end = ERA_YEAR_MAP[era_filter]
                if start <= year <= end:
                    boost += 0.2
            except:
                pass

        if text_filter.strip():
            keywords = text_filter.lower().split()
            overview_lower = str(row['overview']).lower()
            matches = sum(1 for kw in keywords if kw in overview_lower)
            if matches > 0:
                boost += 0.1 * matches

        scored.append((i, base_score + boost))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:8]

if st.button("🎥 Get Recommendations"):
    recs = recommend(selected_movie, mood, genre, era, text)

    if not recs:
        st.warning("No recommendations found.")
    else:
        cols = st.columns(4)
        for i, rec in enumerate(recs):
            movie = movies_raw.iloc[rec[0]]
            imdb = round(movie['vote_average'], 1)
            stars = "⭐" * int(imdb // 2)

            with cols[i % 4]:
                st.image(get_poster(movie['id']))
                with st.expander(f"{movie['title']} {stars} ({imdb}/10)"):
                    genre_tags = ", ".join(movie['genre_list']) if movie['genre_list'] else "N/A"
                    st.caption(f"Genres: {genre_tags}")
                    try:
                        st.caption(f"Year: {str(movie['release_date'])[:4]}")
                    except:
                        pass
                    st.write(movie['overview'][:200])
                    trailer = get_trailer(movie['id'])
                    if trailer:
                        st.video(trailer)
                    else:
                        st.write("Trailer not available")
                    if st.button("➕ Add to Watchlist", key=f"a{i}"):
                        if movie['title'] not in st.session_state.watchlist:
                            st.session_state.watchlist.append(movie['title'])
                            st.success(f"Added {movie['title']}!")

st.sidebar.title("📌 Watchlist")
if not st.session_state.watchlist:
    st.sidebar.caption("Your watchlist is empty.")

for i, title in enumerate(st.session_state.watchlist):
    c1, c2 = st.sidebar.columns([3, 1])
    if c1.button(title, key=f"view_{i}"):
        st.session_state.selected_watch = title
        st.rerun()
    if c2.button("❌", key=f"remove_{i}"):
        st.session_state.watchlist.remove(title)
        st.rerun()

if st.session_state.selected_watch:
    match = movies_raw[movies_raw['title'] == st.session_state.selected_watch]
    if not match.empty:
        movie = match.iloc[0]
        st.markdown("---")
        st.markdown("## 🎬 Selected Movie")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(get_poster(movie['id']))
        with c2:
            st.write("**Title:**", movie['title'])
            st.write("**IMDb:**", movie['vote_average'])
            st.write("**Genres:**", ", ".join(movie['genre_list']))
            try:
                st.write("**Year:**", str(movie['release_date'])[:4])
            except:
                pass
            st.write(movie['overview'])
            trailer = get_trailer(movie['id'])
            if trailer:
                st.video(trailer)
