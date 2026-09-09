# Requêtes SQL De Contrôle Qualité

Ces requêtes servent à produire des rapports complémentaires depuis PostgreSQL. Elles ne modifient aucune donnée et peuvent être rejouées après chaque import, campagne VIES ou réconciliation.

## 01 - Répartition Des Verdicts Structurels

Montre combien de lignes sont structurellement valides ou rejetées avant VIES.

```sql
SELECT
  vr.structure_verdict,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.structure_verdict
ORDER BY total DESC, vr.structure_verdict;
```

## 02 - Répartition Des Motifs Structurels

Détaille les motifs métier associés à la validation structurelle.

```sql
SELECT
  vr.structure_reason,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.structure_reason
ORDER BY total DESC, vr.structure_reason;
```

## 03 - Cas À Réviser Humainement En Phase 1

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

## 04 - Répartition Par Pays Déclaré

Permet de voir le poids de chaque pays dans le référentiel.

```sql
SELECT
  vr.pays_declare_normalise,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.pays_declare_normalise
ORDER BY total DESC, vr.pays_declare_normalise;
```

## 05 - Formats Invalides Par Pays

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

## 06 - Sources De Saisie Les Plus Problématiques

Croise les sources de saisie et les motifs structurels pour repérer les canaux les plus risqués.

```sql
SELECT
  vr.source_saisie,
  vr.structure_reason,
  count(*) AS total
FROM vat_records vr
GROUP BY vr.source_saisie, vr.structure_reason
ORDER BY vr.source_saisie, total DESC, vr.structure_reason;
```

## 07 - Numéros TVA Nettoyés Uniques

Mesure le volume unique réel après nettoyage.

```sql
SELECT
  count(DISTINCT NULLIF(vr.numero_tva_nettoye, '')) AS numeros_nettoyes_uniques
FROM vat_records vr;
```

## 08 - Candidats VIES Uniques

Compte les numéros structurellement valides qui peuvent être appelés auprès de VIES.

```sql
SELECT
  count(*) AS candidats_vies_uniques
FROM vies_candidates;
```

## 09 - Appels VIES Évités

Compare les 10 000 lignes source avec le nombre de candidats VIES uniques.

```sql
SELECT
  (SELECT count(*) FROM vat_records) AS lignes_source,
  (SELECT count(*) FROM vies_candidates) AS candidats_vies_uniques,
  (SELECT count(*) FROM vat_records) - (SELECT count(*) FROM vies_candidates)
    AS appels_vies_evites;
```

## 10 - Doublons Par Numéro Nettoyé

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

## 11 - Verdicts VIES Courants

Résume les derniers verdicts VIES exploitables stockés.

```sql
SELECT
  vv.vies_verdict,
  count(*) AS total
FROM vies_verifications vv
GROUP BY vv.vies_verdict
ORDER BY total DESC, vv.vies_verdict;
```

## 12 - Tentatives VIES Historisées

Résume toutes les tentatives VIES, y compris les erreurs et indéterminés.

```sql
SELECT
  va.vies_verdict,
  count(*) AS total
FROM vies_attempts va
GROUP BY va.vies_verdict
ORDER BY total DESC, va.vies_verdict;
```

## 13 - Numéros En Attente De VIES

Compte les candidats structurellement valides qui n'ont pas encore de verdict VIES exploitable.

```sql
SELECT
  count(*) AS numeros_vies_en_attente
FROM vies_candidates vc
LEFT JOIN vies_verifications vv
  ON vv.numero_tva_nettoye = vc.numero_tva_nettoye
WHERE vv.numero_tva_nettoye IS NULL;
```

## 14 - Verdict Final Par Ligne Source

Répond directement à la question centrale du brief : valides, invalides ou indéterminés.

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

## 15 - Dernières Tentatives VIES

Affiche les derniers appels VIES pour vérifier la reprise, les origines et les erreurs éventuelles.

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
