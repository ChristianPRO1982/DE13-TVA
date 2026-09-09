# Phase 2 - Verification VIES, API et reconciliation

Objectif pour Codex : verifier en ligne uniquement les candidats utiles, stocker les resultats, exposer une API robuste et produire le rapport final.

Cette phase part du resultat de `docs/phase1.md`. Elle ne doit pas refaire des appels reseau pour les lignes deja tranchees structurellement ni pour des numeros nettoyes deja verifies.

Brief source : `brief/brief.md`

## Principes non negociables

- Toujours distinguer `valide`, `invalide` et `indetermine`.
- Une erreur reseau, un timeout ou une indisponibilite VIES donne `indetermine`, jamais `invalide`.
- Un verdict doit toujours avoir une origine et une date.
- Une campagne interrompue doit reprendre sans rappeler les numeros deja verifies.
- Le mode echantillon doit etre disponible des le debut.
- Les codes impossibles ou ambigus doivent pouvoir sortir dans un fichier de revision humaine.

## Client VIES

Avant la campagne, prevoir un client isole, testable, avec timeout explicite.

Endpoint REST attendu par le brief :

```text
https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{countryCode}/vat/{vatNumber}
```

Le client doit recevoir un numero deja nettoye, puis separer :

- code pays VIES ;
- numero national sans prefixe pays.

Exemple :

```text
FR27552032534 -> countryCode=FR, vatNumber=27552032534
```

Reponse a stocker :

- verdict fonctionnel : `valide`, `invalide`, `indetermine` ;
- date de verification ;
- payload brut utile ou message d'erreur ;
- statut HTTP si disponible ;
- temps de reponse si disponible.

## Campagne de verification

La campagne doit travailler sur les numeros uniques issus de la phase 1 :

- candidats structurellement acceptables ;
- dedoublonnes sur `numero_tva_nettoye` ;
- non deja verifies, sauf option explicite de rafraichissement ;
- limites par `--sample-size` si demande.

Commandes attendues :

```bash
uv run python -m de13_tva.pipeline verify-vies --sample-size 200
uv run python -m de13_tva.pipeline verify-vies --limit 50 --delay 1.0
uv run python -m de13_tva.pipeline verify-vies --refresh-days 30
```

Comportements attendus :

- temporisation configurable entre les appels ;
- logs lisibles : numero, rang, verdict, duree, erreur eventuelle ;
- commit en base apres chaque reponse ou petit lot pour permettre la reprise ;
- pas de rappel si une verification exploitable existe deja ;
- possibilite de relancer la meme commande apres interruption.

## Fraicheur des verdicts

Proposition par defaut :

- un verdict VIES est considere frais pendant 30 jours pour l'API ;
- au-dela, l'API peut retourner la valeur connue avec origine `stored_stale` ou tenter un appel VIES frais selon l'option retenue ;
- un numero facture hors taxe devrait etre reverifie si le dernier verdict est trop ancien.

Cette duree doit rester configuree par variable ou constante documentee.

## API FastAPI

L'API doit verifier les numeros recus de maniere robuste, y compris lorsque l'appelant envoie une saisie bruitee.

Nettoyage en entree :

- conserver la valeur brute recue par l'API ;
- supprimer tous les caracteres non alphanumeriques ;
- passer en majuscules ;
- exemple : `AA 9999 9999`, `AA-9999.9999`, `AA/9999_9999` -> `AA99999999` ;
- refuser ou classer `indetermine` si le nettoyage produit une valeur vide ;
- marquer `needs_human_review=true` si le pays est absent, hors UE, ambigu ou contredit par le prefixe du numero.

Endpoint minimal recommande :

```text
GET /vat/{numero_tva}
```

Parametres optionnels utiles :

- `force_refresh=true` pour demander un appel VIES frais ;
- `max_age_days=30` pour controler la fraicheur acceptee.

Contrat de reponse minimal :

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

- `vies_fresh` : appel VIES realise pendant la requete ;
- `stored_fresh` : verdict connu et encore frais ;
- `stored_stale` : verdict connu mais trop ancien ;
- `structural_reject` : numero impossible avant VIES ;
- `unavailable` : VIES injoignable et pas de verdict exploitable ;
- `human_review` : cas non fiable sans arbitrage humain.

L'API ne doit jamais retourner seulement `true` ou `false`. Le consommateur doit savoir d'ou vient l'information et de quand elle date.

Documentation OpenAPI attendue :

```text
/docs
/openapi.json
```

## Sortie des codes a reviser

La phase 2 doit reutiliser ou completer la sortie humaine de la phase 1.

Cas a sortir :

- entrees API nettoyees mais ambigues ;
- pays hors UE ou inconnu ;
- prefixe pays absent ;
- prefixe pays different du pays declare quand le contexte existe ;
- VIES indisponible sans valeur connue ;
- reponses VIES inattendues ou incompletes ;
- tout cas classe `indetermine` qui peut etre resolu par une correction humaine.

Format recommande :

```text
reports/phase_2/a_reviser.csv
```

ou une table/vue PostgreSQL :

```text
human_review_items
```

## Rapport de reconciliation

Commande attendue :

```bash
uv run python -m de13_tva.pipeline reconciliation-report
```

Le rapport doit contenir :

- total lignes source ;
- total numeros nettoyes uniques ;
- total candidats VIES ;
- appels VIES evites ;
- valides ;
- invalides ;
- indetermines ;
- motifs structurels ;
- erreurs VIES ;
- doublons ;
- cas a reviser humainement.

## Tests a prevoir

- normalisation API avec espaces, points, tirets, slashs, underscores et autres caracteres speciaux ;
- valeur vide ou composee uniquement de caracteres supprimables ;
- pays hors UE ;
- `GB` et `UK` ;
- cache frais vs cache expire ;
- indisponibilite VIES classee `indetermine` ;
- reprise de campagne sans nouvel appel ;
- contrat JSON de l'API ;
- generation du rapport.

## Criteres d'acceptation

- Une campagne echantillon s'execute avec `--sample-size 200`.
- Une relance ne rappelle pas les numeros deja verifies.
- Les resultats VIES sont stockes avec date et origine.
- L'API nettoie les saisies bruitees et retourne un verdict complet.
- Les cas non fiables sortent en revision humaine.
- Les trois etats `valide`, `invalide`, `indetermine` sont visibles dans les donnees ou dans le rapport.
- Le rapport se regenere par une commande documentee.
