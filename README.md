# Airflow Data Lyon

Projet local de collecte et de transformation des données de mobilité de la
Métropole de Lyon. Airflow orchestre l'ingestion depuis l'API Data Grand Lyon,
le dépôt des fichiers bruts dans un stockage compatible S3 (Garage), leur
chargement dans PostgreSQL, puis leur standardisation et les transformations
dbt.

## Architecture

- **Airflow** exécute les DAGs définis dans `dags/`.
- **Data Grand Lyon** fournit les données de suivi des véhicules via son API.
- **Garage** stocke les fichiers JSON bruts dans un bucket S3.
- **PostgreSQL de transport** est disponible dans le réseau Docker sur le
  service `postgres_transport` et sur le port local `5433`.
- **PostgreSQL Airflow** stocke les métadonnées Airflow et est exposé sur le
  port local `5432`.
- **Garage** est démarré par Compose comme stockage compatible S3, accessible
  depuis les conteneurs sur `http://garaged:3900` et depuis l'hôte sur
  `http://localhost:3900`. Ses données sont persistées dans des volumes Docker.
- **dbt** exécute les modèles du projet `include/dbt`.
- **Streamlit** est une application distincte, démarrée à la demande sur le
  port local `8501`.

Le DAG `dag_datagrandlyon_vehicle_monitoring` collecte les données, les dépose
dans Garage, charge les données en staging puis appelle la procédure de
standardisation PostgreSQL. Le DAG `dag_core_refresh` lance les modèles dbt.

## Prérequis

- Docker Desktop démarré.
- [Astro CLI](https://www.astronomer.io/docs/astro/cli/install-cli) installé.
- PowerShell pour utiliser `start-astro.ps1`.
- Des identifiants API Data Grand Lyon et des identifiants pour le stockage S3
  et PostgreSQL.

## Configuration

Créer un fichier `.env` à la racine du projet. Ce fichier est ignoré par Git :
ne pas y mettre de secrets dans un fichier suivi par Git.

| Variable | Utilisation |
| --- | --- |
| `DATASOURCE_DATA_GRAND_LYON_USERNAME` | Identifiant de l'API Data Grand Lyon |
| `DATASOURCE_DATA_GRAND_LYON_PASSWORD` | Mot de passe de l'API Data Grand Lyon |
| `AWS_ACCESS_KEY_ID` | Identifiant d'accès au stockage S3 |
| `AWS_SECRET_ACCESS_KEY` | Clé secrète du stockage S3 |
| `AWS_S3_BUCKET` | Nom du bucket qui reçoit les fichiers bruts |
| `AWS_S3_URL` | Endpoint S3 joignable depuis les conteneurs Airflow, par exemple `http://garaged:3900` |
| `GARAGE_RPC_SECRET` | Secret hexadécimal de 64 caractères pour les communications internes de Garage |
| `DB_HOST` | Hôte PostgreSQL joignable depuis Docker (par exemple `postgres_transport` pour le service local) |
| `DB_PORT` | Port PostgreSQL depuis le réseau Docker (généralement `5432` pour `postgres_transport`) |
| `DB_NAME` | Nom de la base de données de transport |
| `DB_SCHEMA` | Schéma PostgreSQL utilisé par dbt |
| `DB_USER` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | Mot de passe PostgreSQL |

Le profil dbt `dev` se connecte à PostgreSQL via `127.0.0.1:5433` depuis
l'hôte. Le DAG dbt utilise le profil `prd`, configuré avec `DB_HOST`,
`DB_PORT` et les autres variables ci-dessus.

## Démarrer Airflow et Garage

Dans PowerShell, depuis la racine du projet :

```powershell
.\start-astro.ps1
```

Ajouter `GARAGE_RPC_SECRET` à `.env` avec une valeur aléatoire hexadécimale de
64 caractères (par exemple `python -c "import secrets; print(secrets.token_hex(32))"`).
Le script charge les variables de `.env` et démarre Astro avec `compose.yaml`,
qui lance également Garage. Garage crée au premier démarrage le bucket
`AWS_S3_BUCKET` et la clé d'accès définie par `AWS_ACCESS_KEY_ID` et
`AWS_SECRET_ACCESS_KEY`. Sa configuration est générée par Compose et ses
données restent persistées dans des volumes Docker.

L'interface Airflow est disponible à l'adresse <http://localhost:8080/>. La
base de métadonnées Airflow est exposée sur `localhost:5432`. L'endpoint S3 de
Garage est exposé sur `localhost:3900`.

Pour arrêter l'environnement Airflow :

```powershell
astro dev stop
```

## Démarrer Streamlit (optionnel)

Dans un autre terminal, depuis la racine du projet :

```powershell
docker compose -f compose.streamlit.yaml up --build
```

L'application est disponible à l'adresse <http://localhost:8501/>. Pour
l'arrêter, utilisez `Ctrl+C`, puis :

```powershell
docker compose -f compose.streamlit.yaml down
```

## Tests

Les tests Airflow se trouvent dans `tests/`. Une fois l'environnement Astro
démarré, les lancer avec :

```powershell
astro dev pytest tests/
```

## Structure du projet

```text
dags/
  raw_lake/                 Collecte et dépôt des fichiers bruts
  staging/                  Chargement des données en staging
  standardized_tables/      Standardisation PostgreSQL
  routines/                 Fonctions partagées par les DAGs
include/dbt/                Projet dbt et ses modèles
streamlit/                  Application Streamlit
tests/                      Tests des DAGs
compose.yaml                Services Airflow, Garage et PostgreSQL
compose.streamlit.yaml      Service Streamlit
start-astro.ps1             Démarrage d'Astro et de Garage
```
