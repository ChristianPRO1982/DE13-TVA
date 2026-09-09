# Phase 2 - Vérification VIES, API et réconciliation

Objectif : vérifier en ligne uniquement les candidats utiles, stocker les résultats, exposer une API robuste et produire un rapport final exploitable.

Cette phase part du résultat de `docs/phase1.md`. Elle ne rappelle pas VIES pour les lignes déjà rejetées structurellement ni pour les numéros déjà traités récemment.

Brief source : `brief/brief.md`

## Principes non négociables

- Toujours distinguer `valide`, `invalide` et `indetermine`.
- Une erreur réseau, un timeout ou une indisponibilité VIES donne `indetermine`, jamais `invalide`.
- Un verdict doit toujours avoir une origine et une date.
- Une campagne interrompue doit reprendre sans rappeler les numéros déjà traités.
- Le mode échantillon doit être disponible.
- Les codes impossibles ou ambigus doivent pouvoir sortir dans un fichier de révision humaine.

## Client VIES

Le client VIES est isolé et testable, avec timeout explicite.

Endpoint REST utilisé :

```text
https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{countryCode}/vat/{vatNumber}
```

Le client reçoit un numéro déjà nettoyé, puis sépare :

- le code pays VIES ;
- le numéro national sans préfixe pays.

Exemple :

```text
FR27552032534 -> countryCode=FR, vatNumber=27552032534
```

Réponse stockée :

- verdict fonctionnel : `valide`, `invalide`, `indetermine` ;
- date de vérification ;
- payload brut utile ou message d'erreur ;
- statut HTTP si disponible ;
- temps de réponse si disponible ;
- origine : `campaign` ou `api`.

## Stockage des résultats VIES

Deux niveaux de stockage sont utilisés :

- `vies_attempts` historise toutes les tentatives, y compris les timeouts, erreurs HTTP et réponses inattendues ;
- `vies_verifications` conserve uniquement le dernier verdict courant exploitable par numéro nettoyé unique.

Un résultat `indetermine` ne doit pas écraser un ancien verdict `valide` ou `invalide`. Il est historisé dans `vies_attempts`, puis le dernier verdict exploitable reste disponible pour l'API et la réconciliation.

## Campagne de vérification

La campagne travaille sur les numéros uniques issus de la phase 1 :

- candidats structurellement acceptables ;
- dédoublonnés sur `numero_tva_nettoye` ;
- non déjà traités, sauf option explicite de rafraîchissement ;
- limités par `--sample-size` ou `--limit` si demandé.

Commandes :

```bash
uv run python -m de13_tva.pipeline verify-vies --sample-size 200 --delay 1.0
uv run python -m de13_tva.pipeline verify-vies --limit 50 --delay 1.0
uv run python -m de13_tva.pipeline verify-vies --refresh-days 30
uv run python -m de13_tva.pipeline verify-vies --batch-size 100 --delay 1.0
```

Comportements attendus :

- traitement par lots de 100 candidats par défaut ;
- temporisation configurable entre les appels ;
- progression visible dans le terminal : batch, numéro, rang, verdict, durée ;
- sauvegarde en base après chaque réponse pour permettre la reprise ;
- pas de rappel par défaut si une tentative existe déjà ;
- rafraîchissement possible avec `--refresh-days` ou `--force-refresh`.

## Fraîcheur des verdicts

La fraîcheur par défaut d'un verdict VIES est de 30 jours pour l'API.

Au-delà, l'API tente un appel VIES frais. Si VIES est indisponible et qu'un ancien verdict exploitable existe, l'API retourne ce verdict avec l'origine `stored_stale` et garde la tentative échouée dans l'historique.

## API FastAPI

Endpoint public :

```text
GET /vat?numero=FR%2027%20552%20032%20534
```

Paramètres optionnels :

- `force_refresh=true` pour demander un appel VIES frais ;
- `max_age_days=30` pour contrôler la fraîcheur acceptée.

Nettoyage en entrée :

- conserver la valeur brute reçue par l'API ;
- supprimer tous les caractères non alphanumériques ;
- passer en majuscules ;
- exemple : `AA 9999 9999`, `AA-9999.9999`, `AA/9999_9999` -> `AA99999999` ;
- classer `indetermine` si le nettoyage produit une valeur vide ;
- marquer `needs_human_review=true` si le pays est absent, hors UE, ambigu ou contredit par le préfixe du numéro.

Contrat de réponse :

```json
{
  "input": "FR 27 552 032 534",
  "normalized": "FR27552032534",
  "verdict": "valide",
  "origin": "vies_fresh",
  "checked_at": "2026-09-09T12:00:00Z",
  "freshness_days": 0,
  "needs_human_review": false,
  "review_reason": null
}
```

Origines attendues :

- `vies_fresh` : appel VIES réalisé pendant la requête ;
- `stored_fresh` : verdict connu et encore frais ;
- `stored_stale` : verdict connu mais trop ancien ;
- `structural_reject` : numéro impossible avant VIES ;
- `unavailable` : VIES injoignable et pas de verdict exploitable ;
- `human_review` : cas non fiable sans arbitrage humain.

Documentation OpenAPI :

```text
/docs
/openapi.json
```

## Sortie des codes à réviser

La phase 2 complète la sortie humaine de la phase 1 avec les cas issus de l'API ou des réponses VIES non exploitables.

Sortie :

```text
reports/phase_2/a_reviser.csv
```

Table associée :

```text
human_review_items
```

Les lignes simplement en attente d'appel VIES ne sont pas des cas de revue humaine. Elles sont signalées dans le détail de réconciliation avec `needs_vies_verification=true`.

## Rapport de réconciliation

Commande :

```bash
uv run python -m de13_tva.pipeline reconciliation-report
```

Sorties :

- `reports/phase_2/reconciliation-report.txt` ;
- `reports/phase_2/reconciliation-details.csv`.

Le rapport contient :

- total lignes source ;
- total numéros nettoyés uniques ;
- total candidats VIES ;
- appels VIES évités ;
- verdicts finaux par ligne source ;
- verdicts VIES courants ;
- tentatives VIES historisées ;
- numéros uniques et lignes source encore en attente de VIES ;
- motifs structurels ;
- doublons ;
- cas à réviser humainement.

## Critères d'acceptation

- Une campagne échantillon s'exécute avec `--sample-size 200`.
- Une relance ne rappelle pas les numéros déjà traités.
- Les tentatives VIES sont historisées avec date et origine.
- Le dernier verdict exploitable n'est pas écrasé par une indisponibilité.
- L'API nettoie les saisies bruitées et retourne un verdict complet.
- Les cas non fiables sortent en révision humaine.
- Les trois états `valide`, `invalide`, `indetermine` sont visibles dans les données ou dans le rapport.
- Le rapport se régénère par une commande documentée.
