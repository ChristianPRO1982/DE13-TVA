# Note d'architecture

## Objectif

Le projet répond au besoin de Meridian Distribution : savoir quels numéros de TVA intracommunautaire sont valides, invalides ou indéterminés, puis exposer un service interrogeable avant émission d'une facture hors taxe.

Le traitement est volontairement séparé en deux phases :

- phase 1 : normalisation, validation structurelle, dédoublonnage et chargement PostgreSQL ;
- phase 2 : vérification VIES, stockage daté des verdicts, API FastAPI et réconciliation finale.

## Réduction des appels VIES

Les 10 000 lignes source ne sont pas appelées directement auprès de VIES. Le pipeline applique d'abord :

- un nettoyage tolérant des numéros : suppression des caractères non alphanumériques et passage en majuscules ;
- une validation structurelle par pays sur les dix formats attendus ;
- l'exclusion des pays hors périmètre VIES ou hors référentiel UE local ;
- un dédoublonnage sur `numero_tva_nettoye`.

Après import, le jeu contient actuellement 7 111 candidats VIES uniques. Cela évite 2 889 appels réseau par rapport à une approche naïve qui appellerait VIES une fois par ligne.

## Modèle de données

La table `vat_records` conserve à la fois la donnée reçue et la donnée déduite : pays brut, pays normalisé, numéro brut, numéro nettoyé, verdict structurel, motif et besoin éventuel de revue humaine.

La table `vies_verifications` stocke le verdict VIES courant par numéro nettoyé unique, avec la date de vérification, l'origine, le statut HTTP, le temps de réponse, le payload utile et le message d'erreur éventuel.

La table `vies_attempts` historise les tentatives VIES, y compris les timeouts et réponses indéterminées. Cela permet de tracer une indisponibilité sans écraser un ancien verdict exploitable.

La table `human_review_items` regroupe les cas qui ne doivent pas être tranchés automatiquement : saisies impossibles, incohérences structurelles, indisponibilité VIES sans verdict exploitable ou réponse inattendue.

## Fraîcheur et indéterminés

La fraîcheur par défaut d'un verdict VIES est fixée à 30 jours pour l'API. Un verdict trop ancien peut être rafraîchi par un nouvel appel VIES.

Une indisponibilité VIES, un timeout, une erreur HTTP ou une réponse JSON inattendue donne toujours `indetermine`, jamais `invalide`. Si un ancien verdict exploitable existe, l'API peut le retourner avec l'origine `stored_stale` tout en stockant la nouvelle tentative indéterminée dans l'historique.

Le rapport final consolide chaque ligne source en `valide`, `invalide` ou `indetermine`. Les lignes structurellement rejetées ou non encore vérifiées restent indéterminées plutôt que faussement invalidées. Les lignes simplement en attente d'appel VIES sont signalées par `needs_vies_verification`, séparément de la revue humaine. Le rapport distingue aussi les numéros uniques restant à appeler et les lignes source concernées.

## Limite assumée

Le brief mentionne un module fourni de validation structurelle avec clés de contrôle nationales. Ce module n'est pas présent dans le dépôt. L'implémentation actuelle repose donc sur des formats par pays isolés dans le code, afin de pouvoir remplacer cette couche si le module officiel est ajouté plus tard.
