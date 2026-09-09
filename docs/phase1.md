# Phase 1 - Cadrage, nettoyage et chargement PostgreSQL

Objectif : construire le socle local avant tout appel VIES. La phase 1 lit le CSV source, conserve les valeurs brutes, nettoie les champs utiles, applique une validation structurelle par pays, charge PostgreSQL de façon idempotente et produit les rapports de contrôle dans `reports/phase_1/`.

Brief source : `brief/brief.md`
Exploration source : `data/exploration.ipynb`

## Données

Fichier principal :

```text
data/numeros-tva-6a9dbf50da6b4741045153.csv
```

Colonnes utilisées :

- `id`
- `raison_sociale`
- `pays_declare`
- `numero_tva`
- `date_saisie`
- `source_saisie`

Référentiel local des codes UE :

```text
data/code-eu.csv
```

Ce fichier est une extraction de la page Wikipédia `Modèle:États UE`, réalisée le 09/09/2026. Il sert de source locale pour identifier les pays membres de l'Union européenne dans ce projet.

Constats issus de l'exploration :

- 10 000 lignes source.
- 9 303 numéros TVA nettoyés uniques.
- 15 codes pays déclarés.
- 10 pays dans le périmètre VIES du jeu : `BE`, `DK`, `FI`, `FR`, `IT`, `LU`, `NL`, `PL`, `PT`, `SE`.
- Codes hors référentiel UE présents dans les données : `QQ`, `XX`, `ZZ`.
- Cas hors périmètre VIES à revoir : `GB`, `UK`.
- 260 lignes ont un numéro TVA absent, blanc ou nettoyé vide.

## Nettoyage

Le pipeline conserve toujours la valeur brute et stocke une valeur normalisée séparée.

Pour `numero_tva` :

- suppression de tous les caractères non alphanumériques ;
- passage en majuscules ;
- exemples : `AA 9999 9999`, `AA-9999.9999`, `AA/9999_9999` deviennent `AA99999999` ;
- une valeur vide, blanche ou entièrement supprimée reste invalide et reçoit le motif `numero_tva_absent`.

Pour `pays_declare` :

- trim ;
- passage en majuscules ;
- contrôle dans `data/code-eu.csv` ;
- `GB` et `UK` sont classés hors périmètre VIES ;
- `QQ`, `XX`, `ZZ` sont rejetés comme hors référentiel UE.

## Validation Structurelle

La validation actuelle est volontairement isolée dans le code métier pour pouvoir être remplacée si le module officiel mentionné par le brief est fourni plus tard.

Limite assumée : la phase 1 vérifie les formats et les motifs métier, mais ne prétend pas implémenter toutes les clés de contrôle nationales.

Formats couverts :

- `BE` : `BE` + 10 chiffres
- `DK` : `DK` + 8 chiffres
- `FI` : `FI` + 8 chiffres
- `FR` : `FR` + 2 caractères alphanumériques + 9 chiffres
- `IT` : `IT` + 11 chiffres
- `LU` : `LU` + 8 chiffres
- `NL` : `NL` + 9 chiffres + `B` + 2 chiffres
- `PL` : `PL` + 10 chiffres
- `PT` : `PT` + 9 chiffres
- `SE` : `SE` + 12 chiffres

Motifs produits :

- `ok_structure`
- `numero_tva_absent`
- `pays_absent`
- `pays_hors_referentiel_ue`
- `pays_hors_perimetre_vies`
- `prefixe_pays_incoherent`
- `format_invalide`
- `a_reviser_humainement`

Un `ok_structure` signifie uniquement que le numéro est candidat à une vérification VIES. Il ne prouve pas que le numéro existe, ni qu'il est actif.

## Base PostgreSQL

La table principale est `vat_records`. Elle contient une ligne par enregistrement source avec :

- l'identifiant source `source_id` ;
- la raison sociale ;
- le pays brut et le pays normalisé ;
- le numéro TVA brut et le numéro nettoyé ;
- la date et la source de saisie ;
- le verdict structurel ;
- le motif structurel ;
- les indicateurs de revue humaine ;
- les timestamps techniques.

Le chargement est idempotent : `source_id` est unique et l'import utilise `INSERT ... ON CONFLICT DO UPDATE`.

La vue `vies_candidates` dédoublonne les numéros nettoyés structurellement valides. Elle prépare la phase 2 en évitant d'appeler VIES plusieurs fois pour le même numéro.

## Commandes

```bash
uv run python -m de13_tva.pipeline import-data
uv run python -m de13_tva.pipeline structural-report
uv run python -m de13_tva.pipeline export-human-review
```

Rapports générés :

- `reports/phase_1/import-data.txt`
- `reports/phase_1/structural-report.txt`
- `reports/phase_1/a_reviser.csv`

## Résultats Actuels

Après import complet :

- lignes source : 10 000 ;
- numéros nettoyés uniques : 9 303 ;
- candidats VIES uniques : 7 111 ;
- appels VIES évités avant phase 2 : 2 889 ;
- lignes à revoir humainement en phase 1 : 2 550.

Répartition structurelle observée :

- `ok_structure` : 7 450 ;
- `format_invalide` : 1 770 ;
- `pays_hors_referentiel_ue` : 311 ;
- `numero_tva_absent` : 260 ;
- `pays_hors_perimetre_vies` : 208 ;
- `prefixe_pays_incoherent` : 1.

## Critères D'Acceptation

- Les 10 000 lignes sont chargées en base.
- Les valeurs brutes sont conservées.
- Les numéros TVA sont nettoyés de manière robuste.
- Les pays hors UE et les cas `GB` / `UK` sont identifiés.
- Chaque ligne a un verdict structurel et un motif.
- Les doublons par numéro nettoyé sont détectés.
- Le nombre d'appels VIES évités est chiffré.
- Les cas à revoir humainement sont exportés dans `reports/phase_1/a_reviser.csv`.
- Les tests couvrent la normalisation, les règles pays, les formats attendus, l'export humain et l'idempotence SQL quand PostgreSQL est disponible.
