import streamlit as st
import pandas as pd
import pydeck as pdk

from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

st.title("Welcome to Streamlit!")
st.write("This is a simple Streamlit app.")

st.set_page_config(
    page_title="Suivi des véhicules",
    page_icon="🚌",
    layout="wide",
)

st.title("🚌 Suivi des véhicules en temps réel")

# Actualisation automatique toutes les 10 secondes
st_autorefresh(interval=10_000, key="refresh")

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


# IMPORTANT : remplacer table et colonnes par les vrais noms.
# On conserve la position la plus récente de chaque véhicule.
SQL = text("""
    SELECT vehicle_monitoring_sk, vehicle_ref, valid_until_time, recorded_at_time, line_ref, direction, vehicle_status, delay, longitude, latitude, stop_point_ref, response_timestamp, producer_ref, response_message_identifier, more_data, siri_version, valid_from, valid_to, is_current, attribute_hash, loaded_at
    FROM standardized.std_datagrandlyon_vehicle_monitoring
    WHERE longitude IS NOT NULL
      AND latitude IS NOT NULL
      AND is_current = TRUE
    ORDER BY vehicle_ref, recorded_at_time DESC
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
    st.warning("Aucune position GPS disponible.")
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

filtered = df[
    df["line_ref"].isin(selected_lines)
    & df["direction"].isin(selected_directions)
].copy()

# Éliminer les coordonnées manifestement invalides
filtered = filtered[
    filtered["latitude"].between(-90, 90)
    & filtered["longitude"].between(-180, 180)
].copy()

# Indicateurs
c1, c2, c3 = st.columns(3)
c1.metric("Véhicules affichés", len(filtered))
c2.metric(
    "Lignes",
    filtered["line_ref"].nunique(),
)
c3.metric(
    "Courses en cours",
    filtered["vehicle_status"].eq("IN_PROGRESS").sum(),
)

if filtered.empty:
    st.info("Aucun véhicule pour les filtres sélectionnés.")
    st.stop()

# Carte : PyDeck utilise latitude puis longitude
view = pdk.ViewState(
    latitude=float(filtered["latitude"].mean()),
    longitude=float(filtered["longitude"].mean()),
    zoom=11,
    pitch=0,
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered,
    get_position="[longitude, latitude]",
    get_radius=65,
    radius_min_pixels=5,
    radius_max_pixels=12,
    get_fill_color=[0, 120, 255, 200],
    pickable=True,
    auto_highlight=True,
)

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
    layers=[layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/"
              "positron-gl-style/style.json",
)

st.pydeck_chart(deck, use_container_width=True)

st.subheader("Positions des véhicules")
st.dataframe(
    filtered.sort_values("recorded_at_time", ascending=False),
    use_container_width=True,
    hide_index=True,
)
