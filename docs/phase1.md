# Phase 1 - Cadrage, nettoyage, reduction et chargement

Objectif pour Codex : construire le socle de donnees avant tout appel VIES.

Cette phase doit produire une base PostgreSQL chargée avec les 10 000 lignes, les valeurs brutes conservées, les valeurs nettoyées/normalisées, le verdict structurel et son motif. Elle doit aussi chiffrer le nombre d'appels VIES évités.

Brief source : `brief/brief.md`
Exploration source : `data/exploration.ipynb`

## Donnees a prendre en compte

Fichier principal :

```text
data/numeros-tva-6a9dbf50da6b4741045153.csv
```

Colonnes :

- `id`
- `raison_sociale`
- `pays_declare`
- `numero_tva`
- `date_saisie`
- `source_saisie`

Referentiel local des codes UE :

```text
data/code-eu.csv
```

Ce fichier vient d'une extraction de la page Wikipedia `Modele:Etats UE` realisee le 09/09/2026. Il sert uniquement a identifier les codes pays membres de l'Union europeenne dans le jeu.

Constats de l'exploration :

- 10 000 lignes.
- 5 sources de saisie : `reprise_erp` (2 071), `crm` (2 019), `portail_client` (1 990), `saisie_manuelle` (1 976), `import_fournisseur` (1 944).
- 15 codes pays declares.
- Codes UE presents dans le jeu : `BE`, `DK`, `FI`, `FR`, `IT`, `LU`, `NL`, `PL`, `PT`, `SE`.
- Codes hors referentiel UE : `QQ`, `XX`, `ZZ`.
- Cas particuliers : `GB` et `UK`, presents dans les donnees mais hors Union europeenne.
- 260 lignes contiennent au moins une valeur vide ou aberrante sur l'ensemble des colonnes.
- 205 lignes ont un `numero_tva` vide ou blanc : 146 valeurs manquantes et 59 valeurs composees uniquement d'espaces.
- Aucun caractere interdit detecte dans `numero_tva` avec la regle d'exploration actuelle, qui accepte lettres, chiffres, espaces, points et tirets.

## Regles de nettoyage

Le nettoyage doit etre tolerant et conserver la trace de la valeur d'origine.

Pour `numero_tva` :

- conserver `numero_tva_brut` exactement tel qu'il est dans le CSV ;
- produire `numero_tva_nettoye` en supprimant tous les caracteres non alphanumeriques, puis en passant en majuscules ;
- exemple : `AA 9999 9999`, `AA-9999.9999`, `AA/9999_9999` doivent devenir `AA99999999` ;
- ne jamais transformer une valeur vide, blanche ou manquante en numero valide ;
- signaler toute valeur nettoyee vide comme `numero_tva_absent`.

Pour `pays_declare` :

- trim + uppercase ;
- verifier l'appartenance au referentiel local `data/code-eu.csv` ;
- `QQ`, `XX`, `ZZ` doivent sortir en rejet structurel ;
- `GB` et `UK` doivent etre traites comme cas a reviser ou hors perimetre UE, pas comme des pays UE valides ;
- ne pas inventer de correction automatique pays si elle n'est pas justifiee.

Pour les champs non TVA :

- conserver les valeurs brutes ;
- reperer les champs vides, blancs, `-`, `null`, `N/A` ;
- ne pas bloquer le chargement global pour une anomalie de champ non critique, mais la rendre visible dans les motifs ou dans un rapport.

## Validation structurelle

Le brief annonce un module fourni de validation structurelle des dix pays du jeu. Si le module est present dans le depot, l'utiliser tel quel et documenter ses motifs.

Si le module n'est pas present :

- creer une interface interne stable pour la validation structurelle ;
- implementer au minimum les motifs necessaires au pipeline ;
- isoler le code pour pouvoir remplacer facilement l'implementation par le module fourni si celui-ci est ajoute plus tard.

Motifs minimaux attendus :

- `ok_structure` ;
- `numero_tva_absent` ;
- `pays_absent` ;
- `pays_hors_referentiel_ue` ;
- `pays_hors_perimetre_vies` ;
- `format_invalide` ;
- `cle_controle_invalide` si la verification de cle est disponible ;
- `a_reviser_humainement` pour les cas nettoyes mais ambigus.

Un verdict structurel `ok_structure` signifie seulement que le format local semble correct. Il ne prouve pas que le numero existe ni qu'il est actif au moment de la facturation.

## Base PostgreSQL

Creer un schema versionne qui distingue le recu du deduit.

Table principale recommandee : `vat_records`.

Champs minimaux :

- `source_id` : id du fichier ;
- `raison_sociale` ;
- `pays_declare_brut` ;
- `pays_declare_normalise` ;
- `numero_tva_brut` ;
- `numero_tva_nettoye` ;
- `date_saisie` ;
- `source_saisie` ;
- `structure_verdict` ;
- `structure_reason` ;
- `needs_human_review` ;
- `human_review_reason` ;
- timestamps techniques.

Contraintes :

- `source_id` unique pour eviter les doublons au rechargement ;
- index sur `numero_tva_nettoye` ;
- index sur `structure_verdict` et `structure_reason`.

Prevoir aussi une table ou une vue dediee aux numeros uniques candidats VIES :

- uniquement les `numero_tva_nettoye` structurellement acceptables ;
- un seul appel VIES par numero nettoye unique ;
- les lignes rejetees structurellement ne doivent pas etre appelees.

## Sortie a reviser humainement

La phase 1 doit produire une sortie exploitable par un humain, par exemple :

```text
reports/a_reviser.csv
```

Elle doit contenir au minimum :

- `source_id` ;
- `raison_sociale` ;
- `pays_declare_brut` ;
- `pays_declare_normalise` ;
- `numero_tva_brut` ;
- `numero_tva_nettoye` ;
- `structure_reason` ;
- `human_review_reason`.

Exemples de cas a inclure :

- pays `GB` ou `UK` ;
- pays `QQ`, `XX`, `ZZ` ;
- numero TVA absent ou blanc ;
- numero nettoye vide ;
- numero nettoye dont le pays prefixe contredit `pays_declare_normalise` ;
- numero nettoye mais dont le format reste non conforme.

## Commandes attendues

Les noms exacts peuvent evoluer, mais la phase 1 doit aboutir a des commandes documentees de ce type :

```bash
uv run python -m de13_tva.pipeline import-data
uv run python -m de13_tva.pipeline structural-report
uv run python -m de13_tva.pipeline export-human-review
```

La commande d'import doit etre idempotente : deux executions consecutives ne doivent pas doubler les lignes.

## Criteres d'acceptation

- Les 10 000 lignes sont chargees en base.
- Les valeurs brutes sont conservees.
- Les numeros TVA sont nettoyes de maniere robuste.
- Les pays hors UE et cas `GB`/`UK` sont identifies.
- Chaque ligne a un verdict structurel et un motif.
- Les doublons par numero nettoye sont detectes.
- Le nombre d'appels VIES évités est chiffré.
- Une sortie des cas a reviser humainement est produite.
- Les tests couvrent au minimum la normalisation, les pays invalides, les valeurs vides et l'idempotence du chargement.
