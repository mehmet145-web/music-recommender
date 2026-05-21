from supabase import create_client
import plotly.graph_objects as go
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os
import streamlit as st
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
load_dotenv()
import sqlite3
import hashlib
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
conn = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT,
    password TEXT
)
""")

conn.commit()
def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()
def auth_screen():

    st.title("🎵 Mini Spotify Login")

    menu = st.selectbox(
        "Seçenek",
        ["Login", "Register"]
    )

    username = st.text_input("Kullanıcı Adı")
    password = st.text_input(
        "Şifre",
        type="password"
    )

    if menu == "Register":

       if st.button("Kayıt Ol"):

        hashed_password = hash_password(password)

        try:

            supabase.table("users").insert({
                "username": username,
                "password_hash": hashed_password
            }).execute()

            st.success("Kayıt başarılı!")

        except Exception as e:

            st.error(f"Kayıt hatası: {e}")

    else:

        if st.button("Giriş Yap"):

            hashed_password = hash_password(password)

            response = supabase.table("users").select("*").eq(
              "username",
             username
            ).eq(
              "password_hash",
               hashed_password
            ).execute()

            user = response.data

            if user:

                st.session_state.logged_in = True
                st.session_state.username = username

                st.success("Giriş başarılı!")
                st.rerun()

            else:

                st.error("Kullanıcı adı veya şifre yanlış.")
                if "logged_in" not in st.session_state:
                   st.session_state.logged_in = False

                if not st.session_state.logged_in:
                    auth_screen()
                    st.stop()

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    )
)
def get_spotify_info(track_name, artist_name):

    try:

        query = f"track:{track_name} artist:{artist_name}"

        search_results = sp.search(
            q=query,
            type="track",
            limit=1
        )

        tracks = search_results["tracks"]["items"]

        if len(tracks) > 0:

            track = tracks[0]

            return {
                "cover_url": track["album"]["images"][0]["url"],
                "spotify_url": track["external_urls"]["spotify"],
                "preview_url": track.get("preview_url")
            }

    except Exception as e:
        st.warning(f"Spotify API hatası: {e}")

    return {
        "cover_url": None,
        "spotify_url": None,
        "preview_url": None
    }
if "username" in st.session_state:

 if "favorites" not in st.session_state:

    response = supabase.table(
        "favorites"
    ).select("*").eq(
        "username",
        st.session_state.username
    ).execute()

    st.session_state.favorites = response.data
if "results" not in st.session_state:
    st.session_state.results = None

df = pd.read_csv("data/dataset.csv")
df = df.sample(2000, random_state=42).reset_index(drop=True)

features = [
    "danceability",
    "energy",
    "acousticness",
    "instrumentalness",
    "valence",
    "tempo",
    "popularity"
]

df = df.dropna(subset=features).reset_index(drop=True)

X = df[features]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    auth_screen()
    st.stop()

st.title("🎵 Mini Spotify Öneri Sistemi")

top_n = st.slider(
    "Kaç öneri gösterilsin?",
    3,
    10,
    5
)

mood = st.selectbox(
    "Mood seç:",
    [
        "Normal",
        "Gym",
        "Sad",
        "Party",
        "Focus",
        "Night Drive"
    ],
    key="mood_select"
)

st.sidebar.title("🎧 Kontrol Paneli")
st.sidebar.write("Toplam şarkı:", len(df))
st.sidebar.write("Seçilen mood:", mood)

if mood == "Gym":
    st.sidebar.success("Yüksek enerji modu")
elif mood == "Sad":
    st.sidebar.info("Düşük valence modu")
elif mood == "Party":
    st.sidebar.warning("Party modu aktif")
elif mood == "Focus":
    st.sidebar.write("Odak modu aktif")
elif mood == "Night Drive":
    st.sidebar.write("Gece sürüş modu")

search = st.text_input("Şarkı ara")

filtered_songs = df[
    df["track_name"].str.contains(search, case=False, na=False)
]["track_name"].unique()

song = st.selectbox(
    "Bir şarkı seç:",
    filtered_songs,
    key="song_select"
)

selected_song = df[df["track_name"] == song]

if selected_song.empty:
    st.warning("Bu aramada şarkı bulunamadı. Lütfen farklı bir kelime dene.")
    st.stop()

selected_song_data = selected_song.iloc[0]
categories = [
    "energy",
    "danceability",
    "valence",
    "acousticness"
]

values = [
    selected_song_data["energy"],
    selected_song_data["danceability"],
    selected_song_data["valence"],
    selected_song_data["acousticness"]
]

fig = go.Figure()

fig.add_trace(go.Scatterpolar(
    r=values,
    theta=categories,
    fill='toself',
    name='Song Features'
))

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 1]
        )
    ),
    showlegend=False
)

st.subheader("📊 Şarkı Özellik Haritası")

st.plotly_chart(fig)

st.sidebar.subheader("🎼 Şarkı Analizi")

for feature in ["energy", "danceability", "valence", "acousticness"]:
    st.sidebar.write(feature.capitalize(), round(selected_song_data[feature], 2))
    st.sidebar.progress(float(selected_song_data[feature]))

if st.button("Öner"):

    if mood == "Normal":

        song_index = df[df["track_name"] == song].index[0]
        selected_genre = df.loc[song_index, "track_genre"]

        same_genre_indices = df[
            df["track_genre"] == selected_genre
        ].index.tolist()

        similarities = cosine_similarity(
            [X_scaled[song_index]],
            X_scaled[same_genre_indices]
        )[0]

        top_positions = similarities.argsort()[-top_n-1:-1][::-1]

        similar_indices = [
            same_genre_indices[i]
            for i in top_positions
        ]

        results = df.iloc[similar_indices]

    elif mood == "Gym":

        results = df[
            (df["energy"] > 0.7) &
            (df["danceability"] > 0.6)
        ].sort_values(by="popularity", ascending=False).head(top_n)

    elif mood == "Sad":

        results = df[
          (df["valence"] < 0.5) &
          (df["energy"] < 0.8)
        ].sort_values(by="popularity", ascending=False).head(top_n)

    elif mood == "Party":

        results = df[
            (df["danceability"] > 0.7) &
            (df["energy"] > 0.65)
        ].sort_values(by="popularity", ascending=False).head(top_n)

    elif mood == "Focus":

        results = df[
            (df["instrumentalness"] > 0.4) |
            (df["acousticness"] > 0.6)
        ].sort_values(by="popularity", ascending=False).head(top_n)

    elif mood == "Night Drive":

        results = df[
            (df["energy"] > 0.4) &
            (df["valence"] > 0.4) &
            (df["tempo"] > 90)
        ].sort_values(by="popularity", ascending=False).head(top_n)

    st.session_state.results = results


if st.session_state.results is not None:

    st.subheader("Benzer Şarkılar")

    results = st.session_state.results[
        [
            "track_name",
            "artists",
            "track_genre",
            "energy",
            "danceability",
            "valence",
            "tempo"
        ]
    ]

    for i, row in results.reset_index(drop=True).iterrows():

        spotify_info = get_spotify_info(
            row["track_name"],
            row["artists"]
        )

        cover_url = spotify_info["cover_url"]
        spotify_url = spotify_info["spotify_url"]
        preview_url = spotify_info["preview_url"]

        if cover_url:
            st.image(cover_url, width=220)

        if spotify_url:
            st.link_button("Spotify’da aç", spotify_url)

        if preview_url:
            st.audio(preview_url)

        st.markdown(
            f"""
            <div style="
                background-color:#1e1e1e;
                padding:20px;
                border-radius:15px;
                margin-bottom:10px;
                border:1px solid #333;
            ">
                <h3>🎵 {row["track_name"]}</h3>
                <p>🎤 <b>Sanatçı:</b> {row["artists"]}</p>
                <p>🎧 <b>Tür:</b> {row["track_genre"]}</p>
                <p>🤖 <b>Neden önerildi?</b> Benzer enerji, dans edilebilirlik ve tempo değerlerine sahip.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button(
            "❤️ Favoriye ekle",
            key=f"fav_{i}_{row['track_name']}"
        ):

           supabase.table("favorites").insert({
           "username": st.session_state.username,
           "track_name": row["track_name"],
           "artists": row["artists"],
           "track_genre": row["track_genre"]
        }).execute()

        st.success("Favoriye eklendi!")

st.sidebar.subheader("❤️ Playlist")

if len(st.session_state.favorites) == 0:

    st.sidebar.write("Henüz favori yok.")

else:

    fav_df = pd.DataFrame(st.session_state.favorites)

    st.sidebar.dataframe(fav_df)

    csv = fav_df.to_csv(index=False).encode("utf-8")

    if "track_name" in fav_df.columns:

        remove_song = st.sidebar.selectbox(
            "Favoriden çıkar:",
            fav_df["track_name"].unique()
        )

        if st.sidebar.button("Sil"):

            supabase.table("favorites").delete().eq(
               "username",
               st.session_state.username
            ).eq(
               "track_name",
               remove_song
            ).execute()

            response = supabase.table(
              "favorites"
            ).select("*").eq(
              "username",
              st.session_state.username
            ).execute()

            st.session_state.favorites = response.data

            st.sidebar.success("Favoriden çıkarıldı!")
            st.rerun()

            pd.DataFrame(
                st.session_state.favorites
            ).to_csv(
                "playlist.csv",
                index=False
            )

            st.sidebar.success("Favoriden çıkarıldı!")
            st.rerun()

    csv = fav_df.to_csv(index=False).encode("utf-8")

    st.sidebar.download_button(
        label="Playlist'i CSV indir",
        data=csv,
        file_name="playlist.csv",
        mime="text/csv",
        key="download_playlist_csv"
    )