# Planning : révisions des paramètres et segments par pharmacie

Spec métier pour tracer **avec quelle révision du moteur de planning** une pharmacie a été gérée dans le temps, afin de calculer une **note terrain** (formule « v1 » existante) sur un sous-ensemble de rapports : *« visites effectuées alors que la pharmacie était sous la révision R »* — et pas seulement sur un mois civique.

**Vocabulaire**

- **Révision planning** : snapshot versionné des poids du moteur (`planning_weights_revisions`). Distinct de la **note terrain v1** (formule sur les rapports).
- **Révision effective au run** : snapshot après fusion *révision active en base + surcharge HTTP éventuelle* lors d’un `POST /planning/run` appliqué (hors prévisualisation).

---

## 1. Segments temporels par pharmacie

Pour chaque pharmacie dont un **run auto appliqué** met à jour le planning calculé par le moteur (en pratique : changement de `next_visit_date` par ce run), on maintient un **historique à intervalles** :

| Champ conceptuel | Sens |
|------------------|------|
| `pharmacy_id` | Pharmacie concernée |
| `revision_id` | Révision planning effective **pour ce segment** |
| `valid_from` | Début (jour métier ; timezone à fixer une fois pour l’ensemble du produit) |
| `valid_to` | Fin **exclusive** du segment : le jour `valid_to` n’appartient plus à ce segment ; `NULL` = segment encore ouvert |

À chaque nouveau run auto qui **touche** cette pharmacie avec une révision effective **E** :

1. Fermer le segment ouvert précédent : `valid_to = date_du_run` (ou veille du run — **une seule convention** pour tout le produit).
2. Ouvrir un segment : `(valid_from = date_du_run, valid_to = NULL, revision_id = E)`.

Référence optionnelle : lier au `planning_run_id` pour audit.

---

## 2. Rattachement d’un rapport de visite à une révision planning

Pour un `visit_report` avec `visit_date = D` et `pharmacy_id = P` :

1. Trouver le segment de **P** tel que `valid_from ≤ D` et (`valid_to` est NULL ou `D < valid_to`).
2. La **révision planning** associée à cette visite est `revision_id` de ce segment.

Toute agrégation « **note sous révision R** » applique la formule terrain habituelle **uniquement** aux rapports dont cette résolution donne **R** (éventuellement en intersection avec filtres commercial, borne temporelle large, etc.).

---

## 3. Replannings manuels — **deux modes** (les deux sont documentés ; **un seul mode actif par configuration produit / tenant**)

Les deux stratégies sont valides métier ; le déploiement choisit **Mode A** ou **Mode B** (réglage configuration — à prévoir côté produit / technique).

### Mode A — Manuel **sans** nouveau segment (simple)

**Comportement**

- Une modification **manuelle** de date / engagement sur la fiche pharmacie **ne crée pas** de nouveau segment et **ne change pas** la révision « planning » attachée à la chronologie issue du moteur.
- La révision restant associée à la période courante reste celle du **dernier run automatique appliqué** qui avait ouvert ou prolongé ce segment, jusqu’au **prochain** run auto qui touche cette pharmacie.

**Intérêt**

- Les essais de paramètres (révisions v1, v2…) restent lisibles sans « bruit » lié aux ajustements ponctuels terrain.
- Les notes « sous révision R » reflètent surtout l’effet **du moteur paramétré en R**, pas les corrections à la main.

**Limite**

- Une visite après un gros réajustement manuel peut encore être étiquetée « sous R » alors que la date affichée ne vient plus du calcul du moteur — acceptable si le métier considère le manuel comme **affinement** sous la même « famille » de décision.

---

### Mode B — Manuel **avec** segment dédié (traçabilité forte)

**Comportement**

- Toute modification **manuelle** qui change la date de prochaine visite (ou équivalent métier défini une fois : ex. champ « prochaine visite » édité hors run auto) **ferme** le segment courant et **ouvre** un segment avec une révision dédiée, par exemple :
  - révision technique **`manual`** / libellé « Hors moteur », ou
  - révision nominale stable réutilisable pour tous les manuels.

**Intérêt**

- Distinction nette dans les analyses et dans les notes agrégées : on peut **exclure** ou **traiter à part** tout ce qui n’a pas été produit par une révision de paramètres numérotée (v1, v2…).
- Cohérent si le métier veut dire : « cette visite ne doit pas compter dans le bilan de v2 ».

**Limite**

- Plus de segments et plus de lignes en historique ; les filtres « note sous v2 » devront souvent **exclure** explicitement le segment `manual`.

---

## 4. Synthèse opérationnelle

| Élément | Règle |
|--------|--------|
| Ouverture / fermeture segment | Run **auto** appliqué qui met à jour le planning moteur pour la pharmacie |
| Révision du segment | Révision **effective** de ce run |
| Rapport → révision | Par `visit_date` dans l’intervalle `[valid_from, valid_to)` |
| Note « sous R » | Formule terrain v1 sur rapports résolus vers **R** |
| Manuel | **Mode A** : ignore pour les segments ; **Mode B** : nouveau segment « manual » (ou équivalent) |

---

## 5. Rappel court (slide)

1. Révision planning = paramètres du moteur au moment d’un run appliqué.  
2. Chaque pharmacie a une chronologie **\[valid_from → révision]** mise à jour par les runs **auto**.  
3. Un rapport est « sous R » si sa date tombe dans le segment **R**.  
4. La note « sous R » = même formule terrain que la v1, sur ce sous-ensemble uniquement.  
5. **Manuel** : soit **Mode A** (ne casse pas la révision courante), soit **Mode B** (segment dédié hors numérotation v1/v2…).

---

## 6. Implémentation dans le dépôt (référence technique)

- Table **`pharmacy_planning_revision_segments`** ; révision sentinel **manuel** `revision_number = 0` (`planning_revision_constants.py`).
- Réglage **`planning_runtime_settings.manual_planning_segment_mode`** : `inherit` (Mode A) ou `manual_revision` (Mode B). API : `GET|PUT /api/planning/runtime-config`.
- Runs auto : après `POST /api/planning/run` (non dry-run), fermeture du segment ouvert + nouveau segment (`valid_to` exclusif au sens `[valid_from, valid_to)`).
- Édition **PUT pharmacie** : si `next_visit_date` change et Mode B → segment **manual**.
- Évaluation : `GET /api/planning/evaluation` accepte `planning_weights_revision_id` et `pure_auto_planning_weights_only` (défaut `true`).