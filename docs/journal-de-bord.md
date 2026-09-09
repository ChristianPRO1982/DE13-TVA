# Journal de bord

## Exploration

Le travail a commencé par l'analyse du jeu dans `data/exploration.ipynb`. Les principaux constats sont :

- 10 000 lignes source ;
- 15 codes pays déclarés ;
- 10 codes pays dans le périmètre UE/VIES retenu pour le jeu ;
- présence de valeurs vides, d'espaces seuls et de tirets dans certaines colonnes ;
- cas particuliers `GB` et `UK`, hors Union européenne ;
- codes manifestement hors référentiel local : `QQ`, `XX`, `ZZ`.

L'extraction `data/code-eu.csv` sert de référentiel local des codes UE. Elle provient de la page Wikipédia `Modèle:États UE`, extraite le 09/09/2026.

## Phase 1

La première phase a mis en place :

- le nettoyage tolérant des numéros de TVA ;
- la validation structurelle par formats pays ;
- le chargement PostgreSQL idempotent ;
- la vue des candidats VIES uniques ;
- les rapports dans `reports/phase_1/` ;
- l'export des lignes à réviser humainement.

Résultat actuel après import : 7 111 candidats VIES uniques et 2 889 appels VIES évités avant toute vérification en ligne.

## Phase 2

La deuxième phase a ajouté :

- un client VIES isolé et testable ;
- une campagne reprenable avec temporisation et mode échantillon ;
- le stockage des verdicts VIES datés ;
- une API FastAPI `GET /vat?numero=...` ;
- les rapports dans `reports/phase_2/`.

Les erreurs réseau, timeouts, erreurs HTTP et réponses inattendues sont traités comme `indetermine`.

## Corrections après audit

Un audit de conformité au brief a fait ressortir plusieurs écarts :

- le rapport de réconciliation devait consolider les verdicts par ligne source, pas seulement par vérification VIES stockée ;
- le client VIES devait résister à un JSON valide mais non objet ;
- l'API devait stocker aussi les tentatives VIES indéterminées ;
- un verdict fiable ne devait pas être écrasé par une indisponibilité ultérieure ;
- les lignes en attente d'appel VIES devaient être séparées des cas à réviser humainement ;
- les livrables documentaires devaient être présents ;
- une commande unique de démonstration devait être documentée ;
- la limite de validation par formats devait être explicitée.

Ces corrections ont été intégrées pour rendre le rendu plus défendable en démonstration.

## Points de vigilance

La validation actuelle ne remplace pas une validation nationale complète avec clés de contrôle. Elle suffit pour réduire les appels VIES et isoler les cas impossibles, mais le verdict métier final dépend de VIES.

Les appels VIES restent externes et instables. Les rapports sont donc reproductibles dans leur forme, mais les verdicts obtenus peuvent évoluer dans le temps.
