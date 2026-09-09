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

Ces commandes supposent que PostgreSQL tourne et que `import-data` a deja ete execute. `verify-vies` effectue de vrais appels reseau au service VIES ; pour une demonstration rapide, utiliser un petit echantillon :

```bash
uv run python -m de13_tva.pipeline verify-vies --sample-size 3 --delay 0
```

Chaque commande produit aussi un fichier dans `reports/phase_2/` :

- `verify-vies.txt` ;
- `reconciliation-report.txt` ;
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

Commandes qualite :

```bash
uv run coverage run -m pytest
uv run coverage report -m
uv run ruff check .
```

La commande `import-data` cree le schema PostgreSQL si necessaire et peut etre relancee sans dupliquer les lignes.

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

Resultat actuel de la phase 1 apres import :

- 10 000 lignes chargees ;
- 9 303 numeros nettoyes uniques non vides ;
- 7 111 candidats VIES uniques ;
- 2 889 appels VIES evites avant toute verification en ligne ;
- repartition structurelle : `ok_structure` (7 450), `format_invalide` (1 770), `pays_hors_referentiel_ue` (311), `numero_tva_absent` (260), `pays_hors_perimetre_vies` (208), `prefixe_pays_incoherent` (1).
- sortie humaine : `reports/phase_1/a_reviser.csv`, 2 550 lignes.

Resultat actuel de la phase 2 apres echantillon VIES de 3 numeros :

- 3 verifications VIES stockees ;
- 3 invalides ;
- 0 valide ;
- 0 indetermine ;
- rapport de reconciliation : `reports/phase_2/reconciliation-report.txt` ;
- export humain phase 2 : `reports/phase_2/a_reviser.csv`.

## Sources

- Brief projet : [brief/brief.md](brief/brief.md)
- VIES : https://ec.europa.eu/taxation_customs/vies/
- Formats des numeros de TVA intracommunautaire : https://taxation-customs.ec.europa.eu/taxation/vat/vat-directive/vat-identification-numbers_en
- Extraction codes UE : [data/code-eu.csv](data/code-eu.csv), issue de Wikipedia `Modele:Etats UE`, realisee le 09/09/2026.

## Qualite et robustesse

Points couverts :

- chargement idempotent : relancer l'import ne duplique pas les lignes ;
- separation claire entre valeur brute, valeur normalisee et verdict structurel ;
- nettoyage tolerant des numeros TVA avant validation ;
- sortie dediee aux cas a reviser humainement ;
- tests automatises avec couverture actuelle a 100 % ;
- trois verdicts metier `valide`, `invalide`, `indetermine` ;
- indisponibilite VIES stockee comme indeterminee, jamais comme invalide ;
- campagne VIES reprenable apres interruption ;
- mode echantillon parametrable ;
- temporisation entre appels VIES ;
- logs exploitables ;
- API avec origine et fraicheur du verdict.

## Etat du depot

Deja present :

- donnees CSV et Excel dans `data/` ;
- extraction des codes pays UE dans `data/code-eu.csv` ;
- notebook d'exploration initiale ;
- configuration PostgreSQL via `docker-compose.yml` ;
- configuration d'environnement dans `.env.example` ;
- pipeline phase 1 : import, rapport structurel et export humain ;
- validation structurelle par formats pays ;
- campagne VIES phase 2 ;
- API FastAPI ;
- rapport de reconciliation reproductible ;
- tests automatises.

A venir :

- note d'architecture ;
- journal de bord.
