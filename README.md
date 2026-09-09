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
- 5 sources de saisie : `reprise_erp` (2 071), `crm` (2 019), `portail_client` (1 990), `saisie_manuelle` (1 976), `import_fournisseur` (1 944) ;
- 15 codes pays declares ;
- codes presents dans le referentiel UE local : `BE`, `DK`, `FI`, `FR`, `IT`, `LU`, `NL`, `PL`, `PT`, `SE` ;
- codes hors referentiel UE a traiter explicitement : `QQ`, `XX`, `ZZ` ;
- cas particuliers a arbitrer : `GB` et `UK`, presents dans le fichier mais hors Union europeenne ;
- 260 lignes contiennent au moins une valeur vide ou aberrante sur l'ensemble des colonnes ;
- valeurs aberrantes detectees : 59 champs avec un espace seul, 146 valeurs manquantes, 55 champs contenant `-` ;
- 205 lignes ont un `numero_tva` vide ou blanc : 146 valeurs manquantes et 59 valeurs composees uniquement d'espaces ;
- aucun caractere interdit detecte dans `numero_tva` avec la regle actuelle, qui accepte lettres, chiffres, espaces, points et tirets.

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
