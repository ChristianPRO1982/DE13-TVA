# DE13-TVA

Projet d'ecole Simplon autour de la validation d'un referentiel de 10 000 numeros de TVA intracommunautaire pour Meridian Distribution.

Le but n'est pas seulement de verifier un format : il faut distinguer les numeros valides, invalides et indetermines, puis preparer un service que la facturation pourra interroger avant d'emettre une facture hors taxe.

Brief complet : [brief/brief.md](brief/brief.md)

## Installation et lancement

Prerequis :

- Python 3.12
- uv
- Docker et Docker Compose

Installer les dependances Python :

```bash
uv sync
```

Creer le fichier d'environnement local :

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

Arreter PostgreSQL :

```bash
docker compose down
```

Supprimer le volume si la base doit etre reinitialisee :

```bash
docker compose down -v
```

Parametres DBeaver :

- host : `localhost`
- port : `5435`
- database : `tva`
- user : `meridian`
- password : `meridian`

Commandes utiles pour l'instant :

```bash
uv run python main.py
uv run pytest
uv run ruff check .
```

Cette section sera completee quand le pipeline, l'API et les commandes de rapport seront stabilises.

## Analyse des donnees

L'exploration initiale est dans [data/exploration.ipynb](data/exploration.ipynb).

Fichier source principal :

```text
data/numeros-tva-6a9dbf50da6b4741045153.csv
```

Source complementaire :

```text
data/code-eu.csv
```

Ce fichier liste les Etats membres de l'Union europeenne et leurs codes ISO. Il sert de referentiel local pour distinguer les pays attendus, les pays hors UE et les codes manifestement invalides. Il provient d'une extraction de la page Wikipedia [Modele:Etats UE](https://fr.wikipedia.org/wiki/Mod%C3%A8le:%C3%89tats_UE), realisee le 09/09/2026.

Constats actuels :

- 10 000 lignes ;
- colonnes : `id`, `raison_sociale`, `pays_declare`, `numero_tva`, `date_saisie`, `source_saisie` ;
- 9 610 numeros bruts distincts ;
- 9 304 numeros distincts apres normalisation simple ;
- 119 valeurs vides ou assimilees vides ;
- 1 861 lignes avec des caracteres de saisie parasites ;
- pays attendus dans le jeu : `FR`, `DK`, `BE`, `LU`, `SE`, `PT`, `NL`, `IT`, `PL`, `FI` ;
- pays/code hors perimetre a traiter explicitement : `ZZ`, `QQ`, `GB`, `UK`, `XX`.

Cette analyse sert a justifier la reduction des appels VIES : normaliser, dedoublonner et rejeter les cas structurellement impossibles avant tout appel reseau.

## Qualite et robustesse

Points a preparer pendant le developpement :

- chargement idempotent : relancer l'import ne doit pas dupliquer les lignes ;
- separation claire entre valeur brute, valeur normalisee, verdict structurel et verdict VIES ;
- trois verdicts metier : `valide`, `invalide`, `indetermine` ;
- indisponibilite VIES stockee comme indeterminee, jamais comme invalide ;
- campagne VIES reprenable apres interruption ;
- mode echantillon parametrable ;
- temporisation entre appels VIES ;
- logs exploitables ;
- tests sur la normalisation, les motifs de rejet, la reprise et le contrat API.

## Etat du depot

Deja present :

- donnees CSV et Excel dans `data/` ;
- extraction des codes pays UE dans `data/code-eu.csv` ;
- notebook d'exploration initiale ;
- configuration PostgreSQL via `docker-compose.yml` ;
- configuration d'environnement dans `.env.example` ;
- base de projet Python avec `pyproject.toml`.

A venir :

- pipeline de chargement PostgreSQL ;
- validation structurelle ;
- client VIES ;
- API FastAPI ;
- rapport de reconciliation reproductible ;
- note d'architecture ;
- journal de bord.
