import streamlit as st
import pandas as pd
import pydeck as pdk

from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Suivi des véhicules",
    page_icon="🚌",
    layout="wide",
)

st.title("🚌 Suivi des véhicules en temps réel")

playing = st.session_state.get("playback", False)
st_autorefresh(interval=1_000 if playing else 10_000, key="refresh")

# Connexion PostgreSQL
@st.cache_resource
def get_engine():
    cfg = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg://"
        f"{cfg['user']}:{cfg['password']}@"
        f"{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )
    return create_engine(url, pool_pre_ping=True)


SQL = text("""
    SELECT vehicle_monitoring_sk, vehicle_ref, valid_until_time, recorded_at_time, line_ref, direction, vehicle_status, delay, longitude, latitude, stop_point_ref, response_timestamp, producer_ref, response_message_identifier, more_data, siri_version, valid_from, valid_to, is_current, attribute_hash, loaded_at,
           recorded_at_time >= NOW() - INTERVAL '1 hour' AS is_in_last_hour
    FROM standardized.std_datagrandlyon_vehicle_monitoring
    WHERE longitude IS NOT NULL
      AND latitude IS NOT NULL
      AND (
          recorded_at_time >= NOW() - INTERVAL '1 hour'
          OR is_current = TRUE
      )
    ORDER BY vehicle_ref, recorded_at_time, loaded_at
""")


@st.cache_data(ttl=8)
def load_data():
    with get_engine().connect() as conn:
        df = pd.read_sql(SQL, conn)

    df["recorded_at_time"] = pd.to_datetime(
        df["recorded_at_time"], utc=True
    )
    return df


try:
    df = load_data()
except Exception as e:
    st.error(
        "Impossible de lire les positions. "
        "Vérifie la connexion et les noms de colonnes."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Aucune position GPS enregistrée au cours de la dernière heure.")
    st.stop()

# Filtres
with st.sidebar:
    st.header("Filtres")

    lines = sorted(df["line_ref"].dropna().unique().tolist())
    selected_lines = st.multiselect(
        "Lignes",
        lines,
        default=lines,
    )

    directions = sorted(
        df["direction"].dropna().unique().tolist()
    )
    selected_directions = st.multiselect(
        "Sens de circulation",
        directions,
        default=directions,
    )

# Éliminer les coordonnées manifestement invalides
valid_positions = df[
    df["latitude"].between(-90, 90)
    & df["longitude"].between(-180, 180)
].copy()
filtered = valid_positions[
    valid_positions["line_ref"].isin(selected_lines)
    & valid_positions["direction"].isin(selected_directions)
].copy()

if filtered.empty:
    st.info("Aucun véhicule pour les filtres sélectionnés.")
    st.stop()

# Afficher l'état du parc sur une timeline fixe, avec un pas d'une minute.
recent_times = filtered.loc[
    filtered["is_in_last_hour"].fillna(False),
    "recorded_at_time",
].dropna()
if recent_times.empty:
    st.warning(
        "Aucun déplacement enregistré au cours de la dernière heure. "
        "Les dernières positions connues sont affichées."
    )
    timeline = [pd.Timestamp.now(tz="UTC")]
else:
    timeline = pd.date_range(
        end=pd.Timestamp.now(tz="UTC").floor("min"),
        periods=60,
        freq="min",
    ).tolist()

button_label = (
    "⏸️ Pause"
    if st.session_state.get("playback", False)
    else "▶️ Lecture"
)
if st.button(button_label, disabled=len(timeline) == 1):
    st.session_state["playback"] = not st.session_state.get("playback", False)

if len(timeline) == 1:
    st.session_state["playback"] = False
    st.session_state["timeline_index"] = 0
elif st.session_state.get("playback", False):
    current_index = st.session_state.get("timeline_index", len(timeline) - 1)
    st.session_state["timeline_index"] = (current_index + 1) % len(timeline)

st.session_state["timeline_index"] = min(
    st.session_state.get("timeline_index", len(timeline) - 1),
    len(timeline) - 1,
)
selected_index = st.slider(
    "Position dans la dernière heure",
    min_value=0,
    max_value=max(1, len(timeline) - 1),
    key="timeline_index",
    disabled=len(timeline) == 1,
)
selected_time = pd.Timestamp(timeline[selected_index])
st.caption(f"Positions au {selected_time.strftime('%d/%m/%Y à %H:%M:%S UTC')}")

history_until_time = valid_positions[
    valid_positions["recorded_at_time"] <= selected_time
].sort_values(["recorded_at_time", "loaded_at"])
positions_at_time = history_until_time.drop_duplicates(
    subset="vehicle_ref",
    keep="last",
).copy()
positions_at_time = positions_at_time[
    positions_at_time["line_ref"].isin(selected_lines)
    & positions_at_time["direction"].isin(selected_directions)
].copy()
vehicle_refs_at_time = positions_at_time["vehicle_ref"]
track_history = history_until_time[
    history_until_time["vehicle_ref"].isin(vehicle_refs_at_time)
]
tracks = [
    {"path": points[["longitude", "latitude"]].values.tolist()}
    for _, points in track_history.groupby("vehicle_ref", sort=False)
    if len(points) > 1
]

# Indicateurs de l'état affiché
c1, c2, c3 = st.columns(3)
c1.metric("Véhicules affichés", len(positions_at_time))
c2.metric("Lignes", positions_at_time["line_ref"].nunique())
c3.metric(
    "Courses en cours",
    positions_at_time["vehicle_status"].eq("IN_PROGRESS").sum(),
)

if positions_at_time.empty:
    st.info("Aucun véhicule pour les filtres sélectionnés.")
    st.stop()

# Carte : PyDeck utilise latitude puis longitude
view = pdk.ViewState(
    latitude=float(positions_at_time["latitude"].mean()),
    longitude=float(positions_at_time["longitude"].mean()),
    zoom=11,
    pitch=0,
)

layers = []
if tracks:
    layers.append(
        pdk.Layer(
            "PathLayer",
            data=tracks,
            get_path="path",
            get_width=3,
            width_min_pixels=2,
            get_color=[0, 120, 255, 130],
            pickable=False,
        )
    )

layer = pdk.Layer(
    "ScatterplotLayer",
    data=positions_at_time,
    get_position="[longitude, latitude]",
    get_radius=65,
    radius_min_pixels=5,
    radius_max_pixels=12,
    get_fill_color=[0, 120, 255, 200],
    pickable=True,
    auto_highlight=True,
)
layers.append(layer)

tooltip = {
    "html": """
        <b>Véhicule :</b> {vehicle_ref}<br/>
        <b>Ligne :</b> {line_ref}<br/>
        <b>Sens :</b> {direction}<br/>
        <b>État :</b> {vehicle_status}<br/>
        <b>Position :</b> {recorded_at_time}
    """,
    "style": {"backgroundColor": "#222", "color": "white"},
}

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/"
              "positron-gl-style/style.json",
)

st.pydeck_chart(deck, use_container_width=True)

st.subheader("Positions des véhicules à l'instant sélectionné")
st.dataframe(
    positions_at_time.sort_values("recorded_at_time", ascending=False),
    use_container_width=True,
    hide_index=True,
)
