import streamlit as st
import pandas as pd
import random
import requests

# ---------- CONFIG ----------
TMDB_API_KEY = "63c39d2a4b6cbbe2c300411d8980ade1"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# ---------- LOAD ----------
@st.cache_data
def load_data():
    return pd.read_csv("tmdb_5000_movies.csv")

movies = load_data()
movies = movies[['id','title','overview','genres','vote_average']].dropna()

# ---------- SIMPLE RECOMMENDER (NO SKLEARN) ----------
def recommend(movie):
    indices = movies[movies['title'] == movie].index.tolist()
    if not indices:
        return []
    idx = indices[0]

    # return random 8 movies excluding selected one
    all_indices = list(range(len(movies)))
    all_indices.remove(idx)
    return random.sample(all_indices, 8)

# ---------- SESSION ----------
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

if "selected_watch" not in st.session_state:
    st.session_state.selected_watch = None

# ---------- UI ----------
st.set_page_config(layout="wide")
st.title("🎬 CineAI FINAL PRO")

col1, col2 = st.columns(2)

with col1:
    mood = st.selectbox("Mood", ["Happy","Sad","Thrilling","Romantic"])
    genre = st.selectbox("Genre", ["Action","Comedy","Drama","Horror","Sci-Fi"])

with col2:
    era = st.selectbox("Era", ["2000s","2010s","2020s"])
    text = st.text_input("Describe what you want")

selected_movie = st.selectbox("Base Movie", movies['title'].values)

# ---------- POSTER ----------
def get_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        data = requests.get(url, timeout=5).json()

        if data.get("poster_path"):
            return f"{IMAGE_BASE}{data['poster_path']}"
    except:
        pass

    return "https://via.placeholder.com/300x450?text=No+Image"

# ---------- TRAILER ----------
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

# ---------- BUTTON ----------
if st.button("🎥 Get Recommendations"):

    recs = recommend(selected_movie)

    cols = st.columns(4)

    for i, idx in enumerate(recs):
        movie = movies.iloc[idx]

        score = random.randint(6,10)
        stars = "⭐"*(score//2)

        with cols[i % 4]:

            st.image(get_poster(movie['id']))

            with st.expander(f"{movie['title']} {stars} ({score}/10)"):

                st.write("IMDb:", movie['vote_average'])
                st.write(movie['overview'][:200])

                trailer = get_trailer(movie['id'])
                if trailer:
                    st.video(trailer)
                else:
                    st.write("Trailer not available")

                if st.button("➕ Add", key=f"a{i}"):
                    if movie['title'] not in st.session_state.watchlist:
                        st.session_state.watchlist.append(movie['title'])

# ---------- WATCHLIST ----------
st.sidebar.title("📌 Watchlist")

for i, title in enumerate(st.session_state.watchlist):

    col1, col2 = st.sidebar.columns([3,1])

    if col1.button(title, key=f"view_{i}"):
        st.session_state.selected_watch = title
        st.rerun()

    if col2.button("❌", key=f"remove_{i}"):
        st.session_state.watchlist.remove(title)
        st.rerun()

# ---------- DETAILS ----------
if st.session_state.selected_watch:

    movie = movies[movies['title']==st.session_state.selected_watch].iloc[0]

    st.markdown("## 🎬 Selected Movie")

    col1, col2 = st.columns([1,2])

    with col1:
        st.image(get_poster(movie['id']))

    with col2:
        st.write("Title:", movie['title'])
        st.write("IMDb:", movie['vote_average'])
        st.write(movie['overview'])

        trailer = get_trailer(movie['id'])
        if trailer:
            st.video(trailer)
