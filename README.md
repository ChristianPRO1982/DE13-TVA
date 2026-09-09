# DE13-TVA

Projet d'ecole Simplon : valider un referentiel de numeros de TVA intracommunautaire pour Meridian Distribution.

L'objectif metier est de repondre a la question :

> Parmi les 10 000 numeros fournis, lesquels sont valides, lesquels ne le sont pas, et lesquels n'ont pas pu etre tranches ?

Le brief complet est disponible dans [brief/brief.md](brief/brief.md).

## Contexte

Meridian Distribution facture hors taxe certains clients de l'Union europeenne lorsque leur numero de TVA intracommunautaire est valide. Apres un controle fiscal, l'entreprise veut :

- qualifier son referentiel historique de 10 000 numeros ;
- reduire les appels inutiles au service externe VIES ;
- conserver les verdicts obtenus avec leur date ;
- exposer une API REST utilisable par la facturation avant emission d'une facture hors taxe.

Un numero peut donc aboutir a trois etats fonctionnels :

- `valide` : le numero est confirme comme valide ;
- `invalide` : le numero est confirme comme invalide ;
- `indetermine` : le service ou les donnees disponibles ne permettent pas de conclure.

Une indisponibilite de VIES ne doit jamais etre assimilee a une invalidite.

## Technologies

- Python 3.12
- FastAPI
- PostgreSQL 16
- Docker Compose
- pandas pour l'exploration des donnees
- pytest et ruff pour les controles de qualite
- VIES, service public de verification des numeros de TVA intracommunautaire

## Structure du depot

```text
.
|-- brief/
|   `-- brief.md
|-- data/
|   |-- numeros-tva-6a9dbf50da6b4741045153.csv
|   |-- numeros-tva-6a9dbf5645cb2220920914.xlsx
|   `-- exploration.ipynb
|-- src/
|   `-- de13_tva/
|       |-- __init__.py
|       `-- main.py
|-- tests/
|   `-- __init__.py
|-- docker-compose.yml
|-- pyproject.toml
|-- uv.lock
|-- .env.example
`-- README.md
```

## Donnees

Le jeu fourni contient 10 000 lignes avec les colonnes suivantes :

- `id`
- `raison_sociale`
- `pays_declare`
- `numero_tva`
- `date_saisie`
- `source_saisie`

Premiers constats d'exploration :

- 10 000 lignes ;
- 9 610 numeros bruts distincts ;
- 9 304 numeros distincts apres normalisation simple alphanumerique ;
- 119 valeurs vides ou assimilees vides ;
- 1 861 lignes contenant des caracteres de bruit de saisie ;
- pays declares : `FR`, `DK`, `BE`, `LU`, `SE`, `PT`, `NL`, `IT`, `PL`, `FI`, ainsi que `ZZ`, `QQ`, `GB`, `UK`, `XX`.

Les pays hors perimetre ou suspects doivent etre traites explicitement dans les motifs de rejet.

## Installation

Pre-requis :

- Python 3.12
- uv
- Docker et Docker Compose

Installer les dependances :

```bash
uv sync
```

Creer la configuration locale :

```bash
cp .env.example .env
```

Valeurs attendues pour PostgreSQL :

```env
POSTGRES_DB=tva
POSTGRES_USER=meridian
POSTGRES_PASSWORD=meridian
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
```

## Lancer PostgreSQL

```bash
docker compose up -d
```

Arreter la base :

```bash
docker compose down
```

Purger le volume PostgreSQL si la base doit etre recreee depuis zero :

```bash
docker compose down -v
```

Parametres DBeaver :

- driver : PostgreSQL
- host : `localhost`
- port : `5435`
- database : `tva`
- utilisateur : `meridian`
- mot de passe : `meridian`

## Commandes de developpement

Lancer le point d'entree actuel :

```bash
uv run python main.py
```

Lancer les tests :

```bash
uv run pytest
```

Lancer ruff :

```bash
uv run ruff check .
```

## Pipeline attendu

Le pipeline final doit suivre l'ordre impose par le brief :

1. charger le fichier source ;
2. normaliser les numeros de TVA ;
3. dedoublonner sur la valeur normalisee ;
4. appliquer la validation structurelle ;
5. exclure des appels VIES les numeros structurellement rejetes ;
6. appeler VIES uniquement pour les numeros candidats ;
7. stocker le verdict en ligne, son origine et sa date ;
8. produire un rapport de reconciliation.

Le schema PostgreSQL doit conserver separement :

- la valeur brute recue ;
- la valeur normalisee ;
- le pays declare ;
- le verdict structurel ;
- le motif structurel ;
- le verdict VIES ;
- la date de verification ;
- la reponse ou le motif d'indetermination.

Un rechargement ne doit pas dupliquer les lignes.

## API attendue

L'API REST devra permettre a la facturation de verifier un numero avant emission hors taxe.

Contrat minimal de reponse :

```json
{
  "numero_tva": "FR27552032534",
  "verdict": "valide",
  "origine": "vies_frais",
  "date_verification": "2026-09-09T12:00:00Z",
  "fraicheur_jours": 0
}
```

L'origine doit distinguer au minimum :

- une reponse fraiche obtenue depuis VIES ;
- une valeur deja connue en base ;
- une impossibilite de conclure.

La documentation OpenAPI devra etre disponible via FastAPI.

## Rapport attendu

Le rapport de reconciliation doit pouvoir etre regenere par une commande et contenir :

- le nombre de numeros valides ;
- le nombre de numeros invalides ;
- le nombre de numeros indetermines ;
- les motifs de rejet structurel ;
- les doublons detectes ;
- la reduction chiffree du nombre d'appels VIES par rapport aux 10 000 lignes initiales.

## Etat d'avancement

Realise :

- depot initialise ;
- donnees CSV et Excel presentes ;
- exploration initiale dans `data/exploration.ipynb` ;
- configuration PostgreSQL via Docker Compose alignee sur le kit du brief ;
- dependances Python declarees dans `pyproject.toml`.

A implementer :

- module de normalisation et validation structurelle ;
- schema SQL et chargement idempotent en PostgreSQL ;
- client VIES ;
- campagne de verification avec mode echantillon, temporisation, logs et reprise ;
- API FastAPI ;
- rapport de reconciliation reproductible ;
- note d'architecture ;
- journal de bord.

## Auteur

Christian Proisy.
