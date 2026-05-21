import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("data/dataset.csv")

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

similarity_matrix = cosine_similarity(X_scaled)

def recommend(song_name, top_n=5):
    matches = df[df["track_name"] == song_name]

    if matches.empty:
        return pd.DataFrame({"Hata": ["Şarkı bulunamadı."]})

    song_index = matches.index[0]

    similarities = list(enumerate(similarity_matrix[song_index]))
    similarities = sorted(similarities, key=lambda x: x[1], reverse=True)

    recommended_indices = [i[0] for i in similarities[1:top_n+1]]

    return df.iloc[recommended_indices][
        ["track_name", "artists", "track_genre", "popularity"]
    ]