# Manuel — Planning automatique, paramètres versionnés et évaluation terrain

Ce document décrit **l’ensemble du dispositif** lié au planning commercial dans Digestic : comment l’**algorithme** propose une date de prochaine visite, comment les **paramètres** sont stockés et surchargés, comment **tracer** une version des paramètres par pharmacie et dans le temps, et comment **calculer une note terrain** (formule « v1 ») — éventuellement **filtrée par révision de planning**.

Il complète la spec métier des segments : [`planning_revision_segments_metier.md`](./planning_revision_segments_metier.md).

---

## 1. Deux notions à ne pas confondre

| Concept | Rôle | Où ça vit |
|--------|------|-----------|
| **Moteur de planning** | Choisir un **jour** de passage dans un **horizon** (ex. 21 jours), pour chaque pharmacie du portefeuille, avec une **logique de priorités** (stock, retard, capacité, géo légère, etc.). | Code `PlanningWeights` + service `VisitPlanningService` + API `POST /api/planning/run`. |
| **Note terrain « v1 »** | Agréger une **note 0–100** à partir des **rapports de visite réels** (`visit_reports`) : réalisation, stock déclaré, ressenti. **Ce n’est pas** une note sur la qualité mathématique de l’algo de dates. | Domaine `planning_evaluation_v1.py` + API `GET /api/planning/evaluation`. |

Une **révision des paramètres de planning** (JSON versionné en base) pilote **uniquement le moteur**. La **version « v1 »** dans « note terrain v1 » désigne **la formule de la note**, pas la révision des poids du planning.

---

## 2. Données que le planning utilise pour chaque pharmacie

Pour chaque pharmacie **avec commercial**, **sans** `planning_manual_override` (ajustement manuel qui bloque le recalcul auto), le service lit notamment :

- **Dernière prochaine visite** (`next_visit_date`) — ancrage métier.
- **Dernière visite** (`last_visit_at`) — pour cycles et retard si pas de date cible.
- **RDV dur** (`planning_hard_rdv_date`) — jour imposé dans la fenêtre si présent.
- **Dernier rapport de visite** (par `visit_date`) : `stock_status`, et si visite non réalisée : `visit_not_completed_reason` (`pharmacy_closed`, `owner_absent`, `refus`, etc.).
- **Coordonnées** (lat/lon) et **clé quartier** dérivée du CP + ville — pour bonus géographique et densité.

Les pharmacies en **override manuel** sont **exclues** du recalcul automatique.

---

## 3. Comment l’algorithme construit le planning (vue d’ensemble)

**Entrées principales**

- Une **date de référence** (souvent « aujourd’hui »).
- Un **horizon en jours** (ex. 7 à 60).
- Un jeu de **poids** `PlanningWeights` (voir § 5).
- La liste des pharmacies **éligibles** (commercial(s), statut actif ou tous selon l’option).

**Étapes (simplifié)**

1. **Construction de l’horizon** : tous les jours calendaires de `reference_date` à `reference_date + horizon_days - 1`.
2. **Deux groupes**
   - **RDV dur** (`planning_hard_rdv_date` renseigné) : assignation sur ce jour, **clampée** dans l’horizon. Si la capacité du jour est déjà pleine, une **alerte** est posée mais la date est quand même assignée (comportement actuel du moteur).
   - **Flexible** : pour chaque pharmacie, choix du **meilleur jour** dans l’horizon selon un **score**.
3. **Score d’un couple (pharmacie, jour)** pour les flexibles  
   `total = besoin + bonus_géo + bonus_densité + pénalité_capacité`  
   avec :
   - **Besoin** (`_base_need_for_day`) : stock faible / rupture, motif d’échec de visite, retard par rapport à une **ancre** (prochaine visite ou cycle depuis dernière visite), bonus si le jour candidat tombe dans la **même semaine ISO** que l’ancre.
   - **Géo** : faible ; augmente si la pharmacie est **proche du « centre de gravité »** des visites déjà placées ce jour-là (`geo_weight`, `fill_radius_km`).
   - **Densité** : petit bonus si le même **quartier** (CP tronqué + ville) est déjà chargé ce jour (`district_density`).
   - **Capacité** : si le jour a déjà `visits_max_per_day` visites, une **forte pénalité** pousse à chercher un autre jour ; si aucun jour viable, comportement de repli avec alerte possible.

4. **Ordre de traitement des flexibles** : tri décroissant par une priorité globale (max du besoin sur l’horizon) — les cas les plus « urgents » sont placés en premier ; les suivants voient déjà une charge géographique / quartier mise à jour.

5. **Persistance** : pour un run **réel** (non prévisualisation), les `next_visit_date` sont **écrites** en base pour les pharmacies traitées.

Le détail du code : `backend/app/domain/visit_planning_engine.py` (`run_planning_assignment`).

---

## 4. Sens des paramètres `PlanningWeights` (avec exemples)

Ce sont des **nombres qui augmentent le « besoin »** ou la **cohésion géographique**. Plus un besoin est élevé, plus la pharmacie est traitée tôt dans le tri et plus elle tire les scores vers les jours qui maximisent le total.

| Paramètre | Rôle intuitif | Exemple de lecture |
|-----------|----------------|-------------------|
| `stock_out` | Priorité si dernier rapport = **rupture** (`out_of_stock`). | Défaut **120**. Monter à **180** si vous voulez **forcer encore plus** les ruptures avant les autres cas. |
| `stock_low` | Priorité si stock **faible** (`low`). | Défaut **55**. Baisser à **30** si vous voulez que le « low » compte **moins** que les échecs de visite. |
| `failed_closed` | Dernière visite **non réalisée**, motif **pharmacie fermée**. | Défaut **48**. |
| `failed_other` | Autre motif d’échec (`owner_absent`, `refus`, …). | Défaut **22**. Remonter si vous voulez **revoir vite** après refus. |
| `per_day_overdue` | Points **par jour de retard** après une **ancre** (date cible ou cycle depuis dernière visite). | Défaut **10**. À **15**, une pharmacie en retard de **10 jours** gagne **150** points de retard (plafonné par `max_overdue_bonus`). |
| `max_overdue_bonus` | **Plafond** du cumul « retard ». | Défaut **90**. Empêche qu’un seul axe « retard » écrase tout le reste. |
| `in_target_week` | Bonus si le **jour candidat** est dans la **même semaine ISO** que l’ancre. | Défaut **72**. Utile pour **coller** aux engagements sans être jour exact. |
| `geo_weight` | Amplitude du terme **proximité** par rapport au centre du jour. | Défaut **8** (volontairement **faible** vs stock/retard). Monter à **15** pour des **tournées plus groupées**, au prix de moins respecter les urgences « métier » pures. |
| `fill_radius_km` | Au-delà de cette distance, la proximité aux autres visites du jour compte peu. | Défaut **14 km**. Réduire à **10** pour des **clusters plus serrés**. |
| `district_density` | Bonus si le même **quartier** (CP court + ville) est déjà présent ce jour. | Défaut **6**. |
| `visits_max_per_day` | **Capacité max** par commercial **et par jour**. | Défaut **14**. Si vos journées réelles sont **8 passages**, passer à **8** pour que le moteur **répartisse** plus sur la semaine. |
| `default_cycle_days` | Si pas de `next_visit_date` mais **dernière visite** connue : cycle par défaut pour l’ancre. | Défaut **28**. |
| `orphan_horizon_bonus_days` | Tampon pour pharmacies **sans historique** récent dans le calcul d’ancre douce. | Défaut **10**. |

**Exemple combiné** : vous jugez que les **ruptures** dominent trop peu face aux visites « à rejouer » après **refus** : augmentez **`stock_out`** et/ou baiss **`failed_other`** jusqu’à retrouver un équilibre subjectif ; puis observez une **prévisualisation** (dry-run) sur une semaine-type avant d’activer une **nouvelle révision** en base (voir § 6).

---

## 5. Où sont les paramètres et comment ils sont fusionnés

### 5.1 Valeurs par défaut « code »

Les défauts sont définis dans la classe **`PlanningWeights`** (`visit_planning_engine.py`). L’API **`GET /api/planning/weights-defaults`** expose ces valeurs **et** des textes d’aide pour l’UI.

### 5.2 Révisions persistées en base (recommandé en exploitation)

- Table **`planning_weights_revisions`** : chaque ligne est une **révision immuable** (`revision_number`, libellé optionnel, snapshot JSON complet des poids).
- Table **`planning_runtime_settings`** (singleton `id = 1`) : pointeur **`active_revision_id`** vers la révision utilisée **quand la requête de run ne fournit pas** de surcharge `weights`.
- Détail technique et endpoints : routes sous **`/api/planning/`** (`weights-config/active`, `weights-revisions`, etc.) — voir contrôleur `planning_controller.py`.

**Fusion au moment d’un run**

1. On part du snapshot JSON de la **révision active** (s’il existe).
2. Si le client envoie **`weights`** dans `POST /planning/run`, les clés envoyées **remplacent** celles du snapshot pour ce run uniquement (`PlanningWeights.merge` sur l’objet fusionné plat).

Sans révision active en base, la fusion revient aux **défauts code**.

### 5.3 Ancien comportement navigateur

Les paramètres n’étaient plus persistés uniquement dans **`localStorage`** : désormais la **source de vérité** est la **base**. L’UI admin « Paramètres du planning » crée des **révisions** et peut **réactiver** une ancienne révision.

---

## 6. Recalcul planning : prévisualiser puis appliquer

### Depuis l’interface

- **Prévisualisation** : envoie `dry_run: true` — **aucune écriture** des dates ; la réponse contient un aperçu (nombre de lignes concernées, etc.).
- **Application** : `dry_run: false` — mise à jour des **`next_visit_date`** pour les pharmacies concernées **non** en override manuel.

Les **poids** utilisés sont ceux de la **révision active** sauf surcharge explicite dans la requête (usage avancé).

### Ce qui est journalisé

- Table **`planning_runs`** : une ligne par exécution (dry-run ou réelle), avec **révision active au moment du run**, présence ou non d’une **surcharge** `weights`, **snapshot des poids réellement appliqués**, périmètre commercial, etc.

---

## 7. Segments « sous quelle révision la pharmacie était planifiée »

Pour répondre au besoin métier « je veux une note **pour les visites faites alors que le planning venait de la révision R** », le système maintient des **segments temporels par pharmacie** :

- Intervalle **`[valid_from, valid_to)`** (**`valid_to` exclus**).
- À chaque **run auto appliqué** qui touche une pharmacie : fermeture du segment ouvert (`valid_to = date du run`) et ouverture d’un nouveau segment avec la **révision de référence** du run et des métadonnées (auto vs manuel, surcharge HTTP ou non).

**Modes replanning manuel** (fiche pharmacie, changement de `next_visit_date`) — **`planning_runtime_settings.manual_planning_segment_mode`** :

- **`inherit` (Mode A)** : pas de nouveau segment ; la chronologie « révision » issue du **dernier auto** reste valide jusqu’au prochain auto.
- **`manual_revision` (Mode B)** : ouverture d’un segment avec la **révision sentinel « manuel »** (`revision_number = 0`), pour isoler les périodes hors moteur numéroté.

Réglage via **`GET` / `PUT /api/planning/runtime-config`** et bloc correspondant dans l’UI admin paramètres planning.

---

## 8. Comment « noter » une version des paramètres de planning

### 8.1 Ce que mesure la note terrain v1

Sur une **période calendaire** `[start_date, end_date]` :

- **Réalisation** (35 %) : part des rapports `completed`.
- **Stock déclaré** (35 %) : moyenne de scores selon `stock_status` (`good`, `low`, `out_of_stock`, `unknown`).
- **Ressenti** (30 %) : moyenne des `feeling_rating` 1→5 transformés en 0–100 ; si aucun ressenti, hypothèse neutre documentée dans le code.

**Important** : cette note reflète **ce que les commerciaux ont saisi sur le terrain**, pas directement « si l’algo de dates était bon ».

### 8.2 Filtrer par révision de **planning** (pas par version de la formule note)

L’endpoint **`GET /api/planning/evaluation`** accepte :

- **`planning_weights_revision_id`** (UUID d’une ligne `planning_weights_revisions`) : ne garde que les rapports dont le **segment** couvrant `visit_date` pointe vers cette révision, sous réserve du garde-fou suivant.
- **`pure_auto_planning_weights_only`** (défaut **`true`**) : exclut les segments **manuel** et les segments **auto** créés lors d’un run ayant eu une **surcharge HTTP `weights`** — pour rapprocher le sous-ensemble d’une config « pure » révision **R**.

La réponse peut inclure **`planning_revision_filter`** avec compteurs d’exclusion (pas de segment, mauvaise révision, filtre pure-auto).

### 8.3 Démarche métier conseillée pour comparer deux configs

1. **Activer / publier** la révision **A**, laisser tourner un **mois** (ou plus) avec des runs auto réels — sans surcharge HTTP si vous voulez des segments « propres » pour le filtre.
2. Calculer la note terrain **avec filtre** `planning_weights_revision_id = A` sur une fenêtre qui couvre les visites sous cette révision (ou une fenêtre large puis lecture des compteurs d’exclusion).
3. Passer à la révision **B**, même protocole.
4. Comparer les notes **et** les volumes (`reports_after_filter`) — si peu de rapports subsistent, la comparaison est **fragile**.
5. Utiliser **Mode B** manuel si vous voulez **exclure** des agrégats « sous R » les périodes où la date a été **corrigiée à la main**.

Limite méthodologique : après coup, changer **B** ne refait pas l’historique ; la robustesse repose sur les **segments** enregistrés **au moment des runs**.

---

## 9. Script de simulation (jeux de données)

Le script **`backend/scripts/simulate_april_camille_planning.py`** (nom générique « avril » mais **année configurable**) peut :

- Réassigner des pharmacies géographiques à un commercial ;
- Pour chaque jour d’un intervalle : **run planning** avec les **poids issus de la révision active** + création de **rapports synthétiques** en ORM (sans facturation) ;
- Mettre à jour les **segments** comme un run réel — sans ligne `planning_runs` pour ce script (référence optionnelle `planning_run_id` vide).

À utiliser sur **environnement de test** uniquement et après migrations Alembic à jour.

---

## 10. Références rapides (fichiers / routes)

| Sujet | Fichier ou route |
|-------|-------------------|
| Moteur planning | `backend/app/domain/visit_planning_engine.py` |
| Service SQL + commit dates | `backend/app/services/visit_planning_service.py` |
| Révisions + runs API | `backend/app/controllers/planning_controller.py` |
| Segments pharmacie | `backend/app/services/pharmacy_planning_segments_service.py`, table `pharmacy_planning_revision_segments` |
| Note terrain v1 | `backend/app/domain/planning_evaluation_v1.py`, `PlanningEvaluationService` |
| Constante UUID révision « manuel » | `backend/app/planning_revision_constants.py` |
| Spec segments métier | `backend/docs/planning_revision_segments_metier.md` |
| UI paramètres / révisions | `frontend/src/pages/Planning/PlanningSettings.jsx` |
| UI évaluation + filtre révision | `frontend/src/pages/Planning/PlanningEvaluation.jsx` |

---

*Document rédigé pour refléter l’état fonctionnel du dépôt au moment de sa création ; en cas de divergence, le code et les migrations Alembic font foi.*
