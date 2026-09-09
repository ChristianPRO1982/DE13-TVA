# Rapport Qualité SQL

## 01 - Répartition des verdicts structurels

Montre combien de lignes sont structurellement valides ou rejetées avant VIES.

```sql
SELECT
  vr.structure_verdict,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.structure_verdict
ORDER BY total DESC, vr.structure_verdict;
```

| structure_verdict | total |
| --- | --- |
| valid | 7450 |
| review | 2550 |

## 02 - Répartition des motifs structurels

Détaille les motifs métier associés à la validation structurelle.

```sql
SELECT
  vr.structure_reason,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.structure_reason
ORDER BY total DESC, vr.structure_reason;
```

| structure_reason | total |
| --- | --- |
| ok_structure | 7450 |
| format_invalide | 1770 |
| pays_hors_referentiel_ue | 311 |
| numero_tva_absent | 260 |
| pays_hors_perimetre_vies | 208 |
| prefixe_pays_incoherent | 1 |

## 03 - Cas à réviser humainement en phase 1

Liste les familles d'anomalies qui ne doivent pas être tranchées automatiquement.

```sql
SELECT
  vr.human_review_reason,
  count(*) AS total
FROM vat_records vr
WHERE vr.needs_human_review = true
GROUP BY vr.human_review_reason
ORDER BY total DESC, vr.human_review_reason;
```

| human_review_reason | total |
| --- | --- |
| Numéro nettoyé non conforme au format attendu pour le pays | 1770 |
| Code pays absent du référentiel UE local | 311 |
| Numéro TVA absent | 260 |
| Pays présent dans le fichier mais hors Union européenne | 208 |
| Préfixe du numéro TVA différent du pays déclaré | 1 |

## 04 - Répartition par pays déclaré

Permet de voir le poids de chaque pays dans le référentiel.

```sql
SELECT
  vr.pays_declare_normalise,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.pays_declare_normalise
ORDER BY total DESC, vr.pays_declare_normalise;
```

| pays_declare_normalise | total |
| --- | --- |
| FR | 974 |
| DK | 961 |
| BE | 959 |
| LU | 956 |
| SE | 949 |
| IT | 947 |
| NL | 947 |
| PT | 947 |
| PL | 939 |
| FI | 902 |
| ZZ | 115 |
| QQ | 109 |
| GB | 104 |
| UK | 104 |
| XX | 87 |

## 05 - Formats invalides par pays

Identifie les pays qui concentrent le plus de formats invalides.

```sql
SELECT
  vr.pays_declare_normalise,
  count(*) AS total
FROM vat_records vr
WHERE vr.structure_reason = 'format_invalide'
GROUP BY vr.pays_declare_normalise
ORDER BY total DESC, vr.pays_declare_normalise;
```

| pays_declare_normalise | total |
| --- | --- |
| SE | 193 |
| IT | 190 |
| NL | 186 |
| FI | 179 |
| BE | 174 |
| DK | 174 |
| FR | 173 |
| PT | 168 |
| LU | 167 |
| PL | 166 |

## 06 - Sources de saisie les plus problématiques

Croise les sources de saisie et les motifs structurels.

```sql
SELECT
  vr.source_saisie,
  vr.structure_reason,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.source_saisie, vr.structure_reason
ORDER BY vr.source_saisie, total DESC, vr.structure_reason;
```

| source_saisie | structure_reason | total |
| --- | --- | --- |
| crm | ok_structure | 1501 |
| crm | format_invalide | 341 |
| crm | pays_hors_referentiel_ue | 65 |
| crm | numero_tva_absent | 57 |
| crm | pays_hors_perimetre_vies | 55 |
| import_fournisseur | ok_structure | 1419 |
| import_fournisseur | format_invalide | 379 |
| import_fournisseur | pays_hors_referentiel_ue | 64 |
| import_fournisseur | numero_tva_absent | 56 |
| import_fournisseur | pays_hors_perimetre_vies | 26 |
| portail_client | ok_structure | 1502 |
| portail_client | format_invalide | 348 |
| portail_client | pays_hors_referentiel_ue | 57 |
| portail_client | numero_tva_absent | 47 |
| portail_client | pays_hors_perimetre_vies | 36 |
| reprise_erp | ok_structure | 1547 |
| reprise_erp | format_invalide | 351 |
| reprise_erp | pays_hors_referentiel_ue | 67 |
| reprise_erp | numero_tva_absent | 59 |
| reprise_erp | pays_hors_perimetre_vies | 47 |
| saisie_manuelle | ok_structure | 1481 |
| saisie_manuelle | format_invalide | 351 |
| saisie_manuelle | pays_hors_referentiel_ue | 58 |
| saisie_manuelle | pays_hors_perimetre_vies | 44 |
| saisie_manuelle | numero_tva_absent | 41 |
| saisie_manuelle | prefixe_pays_incoherent | 1 |

## 07 - Numéros TVA nettoyés uniques

Mesure le volume unique réel après nettoyage.

```sql
SELECT
  count(DISTINCT NULLIF(vr.numero_tva_nettoye, ''))
    AS numeros_nettoyes_uniques
FROM vat_records vr;
```

| numeros_nettoyes_uniques |
| --- |
| 9303 |

## 08 - Candidats VIES uniques

Compte les numéros structurellement valides qui peuvent être appelés auprès de VIES.

```sql
SELECT
  count(*) AS candidats_vies_uniques
FROM vies_candidates;
```

| candidats_vies_uniques |
| --- |
| 7111 |

## 09 - Appels VIES évités

Compare les 10 000 lignes source avec le nombre de candidats VIES uniques.

```sql
SELECT
  (SELECT count(*) FROM vat_records) AS lignes_source,
  (SELECT count(*) FROM vies_candidates) AS candidats_vies_uniques,
  (SELECT count(*) FROM vat_records) - (SELECT count(*) FROM vies_candidates)
    AS appels_vies_evites;
```

| lignes_source | candidats_vies_uniques | appels_vies_evites |
| --- | --- | --- |
| 10000 | 7111 | 2889 |

## 10 - Doublons par numéro nettoyé

Liste les numéros nettoyés présents sur plusieurs lignes source.

```sql
SELECT
  vr.numero_tva_nettoye,
  count(*) AS total_lignes
FROM vat_records vr
WHERE vr.numero_tva_nettoye <> ''
GROUP BY vr.numero_tva_nettoye
HAVING count(*) > 1
ORDER BY total_lignes DESC, vr.numero_tva_nettoye
LIMIT 50;
```

| numero_tva_nettoye | total_lignes |
| --- | --- |
| NA | 48 |
| NULL | 39 |
| DK71704289 | 6 |
| 0282330178 | 5 |
| DK91970813 | 4 |
| FI64379216 | 4 |
| NL785427788B39 | 4 |
| PL2944016503 | 4 |
| PT100405711 | 4 |
| UK26062918 | 4 |
| 580569925B77 | 3 |
| 79425519 | 3 |
| BE0280780446 | 3 |
| DK03190056 | 3 |
| DK21551082 | 3 |
| DK82581529 | 3 |
| FI00550492 | 3 |
| FI62150298 | 3 |
| FI64257543 | 3 |
| FR11950538631 | 3 |
| IT36586305769 | 3 |
| IT53680520532 | 3 |
| IT55553299044 | 3 |
| IT64902006515 | 3 |
| IT72492360010 | 3 |
| IT757930G3312 | 3 |
| IT84393704717 | 3 |
| NL062228912B37 | 3 |
| PL6392206862 | 3 |
| PT823046656 | 3 |
| SE328575176801 | 3 |
| SE604126160001 | 3 |
| ZZ236109235 | 3 |
| 11015857 | 2 |
| 1151018694 | 2 |
| 15851914620 | 2 |
| 253360018B13 | 2 |
| 282326243 | 2 |
| 307885021B85 | 2 |
| 362793827B08 | 2 |
| 385043235B05 | 2 |
| 479254400 | 2 |
| 486602710701 | 2 |
| 514947063 | 2 |
| 5504411220 | 2 |
| 56409513 | 2 |
| 58560322811 | 2 |
| 60999479674 | 2 |
| 74447546 | 2 |
| 757548172 | 2 |

## 11 - Verdicts VIES courants

Résume les derniers verdicts VIES exploitables stockés.

```sql
SELECT
  vv.vies_verdict,
  count(*) AS total
FROM vies_verifications vv
GROUP BY vv.vies_verdict
ORDER BY total DESC, vv.vies_verdict;
```

| vies_verdict | total |
| --- | --- |
| invalide | 6824 |
| valide | 144 |

## 12 - Tentatives VIES historisées

Résume toutes les tentatives VIES, y compris les erreurs et indéterminés.

```sql
SELECT
  va.vies_verdict,
  count(*) AS total
FROM vies_attempts va
GROUP BY va.vies_verdict
ORDER BY total DESC, va.vies_verdict;
```

| vies_verdict | total |
| --- | --- |
| invalide | 6824 |
| valide | 144 |
| indetermine | 143 |

## 13 - Numéros en attente de VIES

Compte les candidats qui n'ont pas encore de verdict VIES exploitable.

```sql
SELECT
  count(*) AS numeros_vies_en_attente
FROM vies_candidates vc
LEFT JOIN vies_verifications vv
  ON vv.numero_tva_nettoye = vc.numero_tva_nettoye
WHERE vv.numero_tva_nettoye IS NULL;
```

| numeros_vies_en_attente |
| --- |
| 143 |

## 14 - Verdict final par ligne source

Répond directement à la question centrale du brief.

```sql
SELECT
  CASE
    WHEN vr.structure_verdict <> 'valid' THEN 'indetermine'
    WHEN vv.vies_verdict = 'valide' THEN 'valide'
    WHEN vv.vies_verdict = 'invalide' THEN 'invalide'
    ELSE 'indetermine'
  END AS verdict_final,
  count(*) AS total
FROM vat_records vr
LEFT JOIN vies_verifications vv
  ON vv.numero_tva_nettoye = vr.numero_tva_nettoye
GROUP BY verdict_final
ORDER BY total DESC, verdict_final;
```

| verdict_final | total |
| --- | --- |
| invalide | 7148 |
| indetermine | 2697 |
| valide | 155 |

## 15 - Dernières tentatives VIES

Affiche les derniers appels VIES pour vérifier reprise, origines et erreurs.

```sql
SELECT
  va.checked_at,
  va.numero_tva_nettoye,
  va.vies_verdict,
  va.origin,
  va.http_status,
  va.response_time_ms,
  va.error_message
FROM vies_attempts va
ORDER BY va.checked_at DESC, va.id DESC
LIMIT 50;
```

| checked_at | numero_tva_nettoye | vies_verdict | origin | http_status | response_time_ms | error_message |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-09 17:15:38.074397+00:00 | FI53300336 | invalide | campaign | 200 | 76 |  |
| 2026-09-09 17:15:37.773608+00:00 | LU98154452 | invalide | campaign | 200 | 89 |  |
| 2026-09-09 17:15:37.459906+00:00 | PT714332224 | invalide | campaign | 200 | 132 |  |
| 2026-09-09 17:15:37.102431+00:00 | PT772064113 | invalide | campaign | 200 | 136 |  |
| 2026-09-09 17:15:36.741528+00:00 | LU87838948 | invalide | campaign | 200 | 122 |  |
| 2026-09-09 17:15:36.393428+00:00 | BE0667627145 | invalide | campaign | 200 | 127 |  |
| 2026-09-09 17:15:36.040418+00:00 | PL7912578287 | invalide | campaign | 200 | 171 |  |
| 2026-09-09 17:15:35.644216+00:00 | SE779153789201 | invalide | campaign | 200 | 359 |  |
| 2026-09-09 17:15:35.059184+00:00 | SE744347222501 | invalide | campaign | 200 | 320 |  |
| 2026-09-09 17:15:34.513252+00:00 | FI30649863 | invalide | campaign | 200 | 336 |  |
| 2026-09-09 17:15:33.951545+00:00 | PL4888034196 | invalide | campaign | 200 | 177 |  |
| 2026-09-09 17:15:33.547849+00:00 | SE646275880301 | invalide | campaign | 200 | 381 |  |
| 2026-09-09 17:15:32.941823+00:00 | NL956716933B37 | invalide | campaign | 200 | 355 |  |
| 2026-09-09 17:15:32.355449+00:00 | BE0728581846 | invalide | campaign | 200 | 2005 |  |
| 2026-09-09 17:15:30.125555+00:00 | DK30825357 | invalide | campaign | 200 | 3627 |  |
| 2026-09-09 17:15:26.273448+00:00 | SE538344367701 | invalide | campaign | 200 | 514 |  |
| 2026-09-09 17:15:25.533629+00:00 | FI07462360 | invalide | campaign | 200 | 76 |  |
| 2026-09-09 17:15:25.231926+00:00 | PT764818934 | invalide | campaign | 200 | 84 |  |
| 2026-09-09 17:15:24.921605+00:00 | DK31019222 | invalide | campaign | 200 | 3750 |  |
| 2026-09-09 17:15:20.946257+00:00 | PT129670375 | invalide | campaign | 200 | 270 |  |
| 2026-09-09 17:15:20.451161+00:00 | LU64090415 | invalide | campaign | 200 | 117 |  |
| 2026-09-09 17:15:20.109779+00:00 | IT35458690753 | invalide | campaign | 200 | 263 |  |
| 2026-09-09 17:15:19.621620+00:00 | DK54092504 | invalide | campaign | 200 | 4091 |  |
| 2026-09-09 17:15:15.305593+00:00 | NL649435382B98 | invalide | campaign | 200 | 138 |  |
| 2026-09-09 17:15:14.942610+00:00 | FR75153894013 | invalide | campaign | 200 | 116 |  |
| 2026-09-09 17:15:14.600688+00:00 | DK62994096 | invalide | campaign | 200 | 4932 |  |
| 2026-09-09 17:15:09.443512+00:00 | LU72353655 | invalide | campaign | 200 | 462 |  |
| 2026-09-09 17:15:08.756690+00:00 | BE0462982186 | invalide | campaign | 200 | 73 |  |
| 2026-09-09 17:15:08.458305+00:00 | IT31301109414 | invalide | campaign | 200 | 72 |  |
| 2026-09-09 17:15:08.160272+00:00 | PL6709190361 | invalide | campaign | 200 | 182 |  |
| 2026-09-09 17:15:07.752631+00:00 | PT905418824 | invalide | campaign | 200 | 449 |  |
| 2026-09-09 17:15:07.077304+00:00 | PL6939489862 | invalide | campaign | 200 | 263 |  |
| 2026-09-09 17:15:06.588331+00:00 | PT734607378 | invalide | campaign | 200 | 98 |  |
| 2026-09-09 17:15:06.263919+00:00 | NL166353085B61 | invalide | campaign | 200 | 543 |  |
| 2026-09-09 17:15:05.495712+00:00 | PT417446792 | invalide | campaign | 200 | 147 |  |
| 2026-09-09 17:15:05.123496+00:00 | PL8087611568 | invalide | campaign | 200 | 246 |  |
| 2026-09-09 17:15:04.652623+00:00 | BE1128721593 | invalide | campaign | 200 | 752 |  |
| 2026-09-09 17:15:03.658501+00:00 | FI97041983 | invalide | campaign | 200 | 433 |  |
| 2026-09-09 17:15:02.999370+00:00 | IT73696792354 | invalide | campaign | 200 | 103 |  |
| 2026-09-09 17:15:02.670351+00:00 | SE742295868101 | invalide | campaign | 200 | 618 |  |
| 2026-09-09 17:15:01.827268+00:00 | NL941015866B85 | invalide | campaign | 200 | 96 |  |
| 2026-09-09 17:15:01.505286+00:00 | DK42075442 | valide | campaign | 200 | 3139 |  |
| 2026-09-09 17:14:58.140860+00:00 | DK64566130 | invalide | campaign | 200 | 100 |  |
| 2026-09-09 17:14:57.815428+00:00 | PT307965481 | invalide | campaign | 200 | 353 |  |
| 2026-09-09 17:14:57.236277+00:00 | SE434897001501 | invalide | campaign | 200 | 345 |  |
| 2026-09-09 17:14:56.665733+00:00 | FR09172480258 | invalide | campaign | 200 | 127 |  |
| 2026-09-09 17:14:56.313598+00:00 | NL774007631B52 | invalide | campaign | 200 | 223 |  |
| 2026-09-09 17:14:55.865368+00:00 | IT31032612462 | invalide | campaign | 200 | 98 |  |
| 2026-09-09 17:14:55.542498+00:00 | IT23813958578 | invalide | campaign | 200 | 78 |  |
| 2026-09-09 17:14:55.238549+00:00 | SE019994435601 | invalide | campaign | 200 | 336 |  |
