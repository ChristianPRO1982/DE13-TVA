# DE13-TVA

**Valider un référentiel de TVA intracommunautaire**

Projet d'école Simplon autour de la validation d'un référentiel de 10 000 numéros de TVA intracommunautaire pour Meridian Distribution.

Le but n'est pas seulement de vérifier un format : il faut distinguer les numéros valides, invalides et indéterminés, puis préparer un service que la facturation pourra interroger avant d'émettre une facture hors taxe.

Brief complet : [brief/brief.md](brief/brief.md)

## Technologies

- Python 3.12 pour le pipeline, les règles métier et les tests.
- PostgreSQL pour stocker les données brutes, normalisées et les verdicts.
- Docker Compose pour lancer la base localement.
- FastAPI et Uvicorn pour exposer le service REST.
- httpx pour interroger VIES avec timeout explicite.
- pytest, coverage et Ruff pour la qualité.

Ces choix restent proches du brief : ils couvrent le traitement local, le stockage relationnel, l'API et la robustesse face à un service externe instable.

## Installation et lancement

Prérequis :

- Python 3.12
- uv
- Docker et Docker Compose

Installer les dépendances Python :

```bash
uv sync
```

Créer le fichier d'environnement local :

```bash
cp .env.example .env
```

Valeurs attendues :

```env
POSTGRES_DB=tva
POSTGRES_USER=meridian
POSTGRES_PASSWORD=meridian
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
```

Lancer PostgreSQL :

```bash
docker compose up -d
```

Commande unique de démonstration, une fois PostgreSQL lancé :

```bash
uv run python -m de13_tva.pipeline demo-run --sample-size 3 --delay 0
```

Cette commande importe les données, régénère les rapports phase 1, lance une campagne VIES échantillon, puis produit les rapports phase 2.

Arrêter PostgreSQL :

```bash
docker compose down
```

Supprimer le volume si la base doit être réinitialisée :

```bash
docker compose down -v
```

Paramètres DBeaver :

- host : `localhost`
- port : `5435`
- database : `tva`
- user : `meridian`
- password : `meridian`

Commandes phase 1 :

```bash
uv run python -m de13_tva.pipeline import-data
uv run python -m de13_tva.pipeline structural-report
uv run python -m de13_tva.pipeline export-human-review
```

Chaque commande produit aussi un fichier dans `reports/phase_1/` :

- `import-data.txt` ;
- `structural-report.txt` ;
- `a_reviser.csv`.

Commandes phase 2 :

```bash
uv run python -m de13_tva.pipeline verify-vies --sample-size 200 --delay 1.0
uv run python -m de13_tva.pipeline reconciliation-report
uv run python -m de13_tva.pipeline export-phase2-human-review
```

Ces commandes supposent que PostgreSQL tourne et que `import-data` a déjà été exécutée. `verify-vies` effectue de vrais appels réseau au service VIES ; pour une démonstration rapide, utiliser un petit échantillon :

```bash
uv run python -m de13_tva.pipeline verify-vies --sample-size 3 --delay 0
```

Chaque commande produit aussi un fichier dans `reports/phase_2/` :

- `verify-vies.txt` ;
- `reconciliation-report.txt` ;
- `reconciliation-details.csv` ;
- `a_reviser.csv`.

Lancer l'API :

```bash
uv run uvicorn de13_tva.api:app --reload
```

Endpoint principal :

```bash
curl --get "http://localhost:8000/vat" --data-urlencode "numero=FR 27 552 032 534"
```

La documentation OpenAPI est disponible sur `/docs` et `/openapi.json`.

Commandes qualité :

```bash
uv run coverage run -m pytest
uv run coverage report -m
uv run ruff check .
```

La commande `import-data` crée le schéma PostgreSQL si nécessaire et peut être relancée sans dupliquer les lignes.

## Analyse des données

L'exploration initiale est dans [data/exploration.ipynb](data/exploration.ipynb).

Fichier source principal :

```text
data/numeros-tva-6a9dbf50da6b4741045153.csv
```

Source complémentaire :

```text
data/code-eu.csv
```

Ce fichier liste les États membres de l'Union européenne et leurs codes ISO. Il sert de référentiel local pour distinguer les pays attendus, les pays hors UE et les codes manifestement invalides. Il provient d'une extraction de la page Wikipédia [Modèle:États UE](https://fr.wikipedia.org/wiki/Mod%C3%A8le:%C3%89tats_UE), réalisée le 09/09/2026.

Constats actuels :

- 10 000 lignes ;
- colonnes : `id`, `raison_sociale`, `pays_declare`, `numero_tva`, `date_saisie`, `source_saisie` ;
- 5 sources de saisie : `reprise_erp` (2 071), `crm` (2 019), `portail_client` (1 990), `saisie_manuelle` (1 976), `import_fournisseur` (1 944) ;
- 15 codes pays déclarés ;
- codes présents dans le référentiel UE local : `BE`, `DK`, `FI`, `FR`, `IT`, `LU`, `NL`, `PL`, `PT`, `SE` ;
- codes hors référentiel UE à traiter explicitement : `QQ`, `XX`, `ZZ` ;
- cas particuliers à arbitrer : `GB` et `UK`, présents dans le fichier mais hors Union européenne ;
- 260 lignes contiennent au moins une valeur vide ou aberrante sur l'ensemble des colonnes ;
- valeurs aberrantes détectées : 59 champs avec un espace seul, 146 valeurs manquantes, 55 champs contenant `-` ;
- 205 lignes ont un `numero_tva` vide ou blanc : 146 valeurs manquantes et 59 valeurs composées uniquement d'espaces ;
- aucun caractère interdit détecté dans `numero_tva` avec la règle actuelle, qui accepte les lettres, les chiffres, les espaces, les points et les tirets.

Cette analyse sert à justifier la réduction des appels VIES : normaliser, dédoublonner et rejeter les cas structurellement impossibles avant tout appel réseau.

Résultat actuel de la phase 1 après import :

- 10 000 lignes chargées ;
- 9 303 numéros nettoyés uniques non vides ;
- 7 111 candidats VIES uniques ;
- 2 889 appels VIES évités avant toute vérification en ligne ;
- répartition structurelle : `ok_structure` (7 450), `format_invalide` (1 770), `pays_hors_referentiel_ue` (311), `numero_tva_absent` (260), `pays_hors_perimetre_vies` (208), `prefixe_pays_incoherent` (1).
- sortie humaine : `reports/phase_1/a_reviser.csv`, 2 550 lignes.

Résultat actuel de la phase 2 après échantillon VIES de 3 numéros :

- 3 verdicts VIES courants stockés ;
- 3 tentatives VIES historisées ;
- 3 invalides ;
- 0 valide ;
- 0 indéterminé ;
- 7 108 numéros VIES uniques encore en attente ;
- 7 446 lignes source encore en attente de VIES ;
- rapport de réconciliation : `reports/phase_2/reconciliation-report.txt` ;
- détail ligne par ligne : `reports/phase_2/reconciliation-details.csv` ;
- export humain phase 2 : `reports/phase_2/a_reviser.csv`.

## Sources

- Brief projet : [brief/brief.md](brief/brief.md)
- VIES : https://ec.europa.eu/taxation_customs/vies/
- Formats des numéros de TVA intracommunautaire : https://taxation-customs.ec.europa.eu/taxation/vat/vat-directive/vat-identification-numbers_en
- Extraction des codes UE : [data/code-eu.csv](data/code-eu.csv), issue de Wikipédia `Modèle:États UE`, réalisée le 09/09/2026.

## Qualité et robustesse

Points couverts :

- chargement idempotent : relancer l'import ne duplique pas les lignes ;
- séparation claire entre valeur brute, valeur normalisée et verdict structurel ;
- nettoyage tolérant des numéros TVA avant validation ;
- sortie dédiée aux cas à réviser humainement ;
- tests automatisés avec une couverture actuelle à 100 % ;
- trois verdicts métier `valide`, `invalide`, `indetermine` ;
- indisponibilité VIES stockée comme indéterminée, jamais comme invalide ;
- campagne VIES reprenable après interruption ;
- mode échantillon paramétrable ;
- temporisation entre appels VIES ;
- logs exploitables ;
- API avec origine et fraîcheur du verdict ;
- rapport de réconciliation consolidé par ligne source ;
- séparation entre revue humaine, numéros uniques en attente de VIES et lignes source concernées ;
- historique des tentatives VIES indéterminées sans écraser le dernier verdict exploitable.

Limite assumée : le module officiel de validation structurelle avec clés de contrôle mentionné dans le brief n'est pas présent dans le dépôt. La validation actuelle repose donc sur des formats par pays, isolés dans le code pour pouvoir être remplacés si ce module est fourni.

## État du dépôt

Déjà présent :

- données CSV et Excel dans `data/` ;
- extraction des codes pays UE dans `data/code-eu.csv` ;
- notebook d'exploration initiale ;
- configuration PostgreSQL via `docker-compose.yml` ;
- configuration d'environnement dans `.env.example` ;
- pipeline phase 1 : import, rapport structurel et export humain ;
- validation structurelle par formats pays ;
- campagne VIES phase 2 ;
- API FastAPI ;
- rapport de réconciliation reproductible ;
- détail de réconciliation ligne par ligne ;
- tests automatisés ;
- note d'architecture : [docs/architecture.md](docs/architecture.md) ;
- journal de bord : [docs/journal-de-bord.md](docs/journal-de-bord.md).

## Auteur

ChristianPRO1982
