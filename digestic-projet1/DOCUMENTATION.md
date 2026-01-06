# Documentation de l'Application GRCP
## Gestion Relation Commerciale Pharmacie

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture technique](#architecture-technique)
3. [Authentification et autorisation](#authentification-et-autorisation)
4. [Fonctionnalités par module](#fonctionnalités-par-module)
5. [Formats de données](#formats-de-données)
6. [Rôles utilisateurs](#rôles-utilisateurs)

---

## Vue d'ensemble

L'application GRCP (Gestion Relation Commerciale Pharmacie) est une solution web complète pour la gestion des relations commerciales entre des commerciaux et des pharmacies. Elle permet de suivre les visites, gérer les factures, planifier les rendez-vous et générer des rapports de visite.

### Technologies utilisées

- **Frontend** : React 18 avec Vite, Material-UI (MUI)
- **Backend** : Python 3 avec Flask
- **Stockage** : Fichiers JSON (prêt pour migration vers base de données)
- **Authentification** : Sessions Flask avec cookies
- **Format de dates** : dd/MM/yyyy

---

## Architecture technique

### Backend

L'architecture backend suit les principes de la programmation orientée objet avec une séparation claire des responsabilités :

#### Structure des packages

```
backend/
├── app/
│   ├── __init__.py          # Configuration Flask, CORS, sessions
│   ├── models/              # Modèles de données (dataclasses)
│   │   ├── pharmacy.py
│   │   ├── visit.py
│   │   ├── visit_report.py
│   │   ├── invoice.py
│   │   ├── user.py
│   │   └── commercial_material.py
│   ├── repositories/        # Accès aux données (fichiers JSON)
│   │   ├── base_repository.py
│   │   ├── pharmacy_repository.py
│   │   ├── visit_repository.py
│   │   └── ...
│   ├── services/            # Logique métier
│   │   ├── pharmacy_service.py
│   │   ├── visit_service.py
│   │   ├── auth_service.py
│   │   └── ...
│   ├── business/            # Logique métier avancée
│   │   └── visit_business.py
│   └── controllers/         # Endpoints API (Flask Blueprints)
│       ├── pharmacy_controller.py
│       ├── visit_controller.py
│       ├── auth_controller.py
│       └── ...
├── data/                    # Fichiers JSON de stockage
│   ├── pharmacies.json
│   ├── users.json
│   ├── visits.json
│   └── ...
└── scripts/
    └── init_data.py         # Génération de données de test
```

#### Points clés de l'architecture

- **Modèles** : Dataclasses Python pour représenter les entités
- **Repositories** : Abstraction pour l'accès aux données, facilitant la migration vers une base de données
- **Services** : Logique métier réutilisable
- **Controllers** : Endpoints RESTful avec gestion des erreurs
- **CORS** : Configuré pour permettre les requêtes depuis le frontend
- **Sessions** : Gestion des sessions utilisateur avec cookies sécurisés

### Frontend

L'architecture frontend suit les meilleures pratiques React avec une structure modulaire :

#### Structure des dossiers

```
frontend/
├── src/
│   ├── components/          # Composants réutilisables
│   │   ├── Layout/
│   │   ├── PharmacyForm/
│   │   ├── VisitReportList/
│   │   ├── VisitReportDetail/
│   │   ├── InvoiceList/
│   │   └── InvoiceDetail/
│   ├── pages/               # Pages principales
│   │   ├── Login/
│   │   ├── Dashboard/
│   │   ├── Pharmacies/
│   │   ├── Visits/
│   │   ├── Planning/
│   │   ├── Invoices/
│   │   └── Users/
│   ├── services/            # Services API
│   │   ├── api.js
│   │   ├── pharmacyService.js
│   │   ├── authService.js
│   │   └── ...
│   └── App.jsx              # Routage principal
```

#### Points clés de l'architecture

- **Composants modulaires** : Séparation claire des responsabilités
- **Services API** : Centralisation des appels API avec Axios
- **Routing** : React Router DOM pour la navigation
- **State Management** : React hooks (useState, useEffect)
- **UI Library** : Material-UI pour une interface cohérente
- **Format de dates** : date-fns pour le formatage (dd/MM/yyyy)

---

## Authentification et autorisation

### Système d'authentification

L'application utilise un système d'authentification basé sur les sessions Flask :

- **Méthode** : Authentification par email (sans mot de passe pour le moment)
- **Sessions** : Stockées côté serveur avec cookies HTTP-only
- **CORS** : Configuré avec `supports_credentials=True` pour les cookies
- **Sécurité** : Cookies avec `SameSite=Lax` et `HttpOnly=True`

### Rôles utilisateurs

#### Admin
- Accès complet à toutes les fonctionnalités
- Peut voir toutes les pharmacies
- Peut créer, modifier et supprimer des pharmacies
- Peut gérer les commerciaux (CRUD complet)
- Accès à toutes les données sans restriction

#### Commercial
- Accès limité aux pharmacies qui lui sont assignées
- Peut consulter les détails de ses pharmacies
- Peut fixer la date de la prochaine visite
- Peut créer des rapports de visite
- Ne peut pas modifier les pharmacies
- Ne peut pas voir les autres commerciaux

### Endpoints d'authentification

- `POST /api/auth/login` : Connexion (email requis)
- `POST /api/auth/logout` : Déconnexion
- `GET /api/auth/me` : Récupération des informations de l'utilisateur connecté

---

## Fonctionnalités par module

### 1. Module de Connexion (Login)

**Page** : `/login`

#### Fonctionnalités

- **Formulaire de connexion** : Champ email pour l'authentification
- **Gestion des erreurs** : Affichage des messages d'erreur en cas d'échec
- **Redirection automatique** : Redirection vers le dashboard après connexion réussie
- **Protection des routes** : Redirection vers `/login` si non authentifié

#### Interface

- Design Material-UI avec validation
- Messages d'erreur clairs
- Indicateur de chargement pendant l'authentification

---

### 2. Module Tableau de Bord (Dashboard)

**Page** : `/`

#### Fonctionnalités

- **Vue d'ensemble** : Statistiques générales de l'application
- **Accès rapide** : Liens vers les principales fonctionnalités
- **Personnalisation** : Affichage adapté selon le rôle (admin/commercial)

---

### 3. Module Pharmacies

**Page** : `/pharmacies`  
**Détail** : `/pharmacies/:id`

#### Fonctionnalités principales

##### Liste des pharmacies (`/pharmacies`)

**Affichage** :
- Tableau avec colonnes : Nom, Adresse, Commercial, Dernière visite, Prochaine visite, Classification, Actions
- Format de dates : dd/MM/yyyy
- Chips colorés pour la classification (A=rouge, B=orange, C=bleu)

**Tri** :
- Tri possible sur toutes les colonnes
- Indicateur visuel (flèche) pour la colonne active
- Ordre ascendant/descendant

**Filtrage multi-critères** :
- Filtres intégrés dans la première ligne du tableau
- Filtres disponibles :
  - **Nom** : Recherche textuelle
  - **Adresse** : Recherche textuelle
  - **Commercial** : Liste déroulante (Tous + liste des commerciaux)
  - **Dernière visite** : Recherche textuelle
  - **Prochaine visite** : Recherche textuelle
  - **Classification** : Liste déroulante (Toutes, A, B, C)
- Les filtres sont combinables (ET logique)
- Bouton "Réinitialiser filtres" visible quand des filtres sont actifs

**Actions** :
- **Double-clic sur une ligne** : Ouvre les détails de la pharmacie
- **Icône œil** : Voir les détails
- **Icône crayon** : Modifier (uniquement pour admin)
- **Bouton "Nouvelle Pharmacie"** : Créer une pharmacie (uniquement pour admin)

**Calcul des dates** :
- **Dernière visite** : Date la plus récente des rapports de visite
- **Prochaine visite** : 
  - Priorité aux visites planifiées (status='planned')
  - Sinon, date la plus proche dans les `next_visit_date` des rapports
  - Prend la date future la plus proche, ou la plus récente si aucune date future

**Autorisations** :
- **Admin** : Voit toutes les pharmacies, peut créer/modifier
- **Commercial** : Voit uniquement ses pharmacies assignées, lecture seule

##### Détail d'une pharmacie (`/pharmacies/:id`)

**Informations affichées** :
- Nom, adresse, code postal, ville
- Informations du pharmacien (nom, email, téléphone)
- Classification avec chip coloré
- Statistiques (nombre de visites, factures, factures en retard)

**Actions disponibles** :
- **Icône "Rapports de visite"** : Liste des rapports de visite
- **Icône "Factures"** : Liste des factures
- **Icône "Calendrier"** (commercial uniquement) : Fixer la date de la prochaine visite
- **Icône "+"** (commercial uniquement) : Ajouter un rapport de visite

**Fonctionnalités commercial** :

1. **Fixer la date de la prochaine visite** :
   - Modal avec champ date
   - Date par défaut : prochaine visite existante (si disponible)
   - Format affiché : dd/MM/yyyy
   - Crée automatiquement un rapport de visite minimal avec cette date

2. **Ajouter un rapport de visite** :
   - Formulaire complet avec :
     - Dépôt effectué (checkbox)
     - Nombre de bouteilles déposées
     - État des stocks (Bon, Faible, Rupture, Inconnu)
     - État du présentoir (En place, Pas en place, Inconnu)
     - État de la couverture (En place, À commander, Inconnu)
     - Taille de couverture à commander (si applicable)
     - Mode de livraison (Normal, Dépôt-vente)
     - Date de la prochaine visite
     - Notes
   - Crée automatiquement une visite planifiée si nécessaire

---

### 4. Module Visites

**Page** : `/visits`  
**Rapport** : `/visits/report/:visitId`

#### Fonctionnalités

##### Liste des visites (`/visits`)

- Tableau avec : Date, Pharmacie, Commercial, Statut, Actions
- Format de dates : dd/MM/yyyy
- Chips colorés pour les statuts :
  - `planned` : Bleu (info)
  - `completed` : Vert (success)
  - `cancelled` : Rouge (error)
  - `postponed` : Orange (warning)
- Bouton "Nouvelle Visite" pour créer une visite planifiée
- Icône pour créer un rapport de visite (si status='planned')

##### Création de rapport de visite (`/visits/report/:visitId`)

Formulaire complet pour créer un rapport de visite :
- Dépôt effectué
- Nombre de bouteilles
- État des stocks
- État du présentoir
- État de la couverture
- Date de la prochaine visite
- Mode de livraison
- Notes

---

### 5. Module Planning

**Page** : `/planning`

#### Fonctionnalités

Vue du planning des visites avec 3 onglets :

##### Onglet "Aujourd'hui"

- Affiche toutes les pharmacies avec une prochaine visite aujourd'hui
- Cartes avec : Nom de la pharmacie, Heure, Commercial
- Bouton pour voir les détails de la pharmacie
- Message si aucune visite planifiée

##### Onglet "Jour"

- Sélecteur de date
- Affiche toutes les pharmacies avec une prochaine visite à la date sélectionnée
- Format de dates : dd/MM/yyyy
- Cartes avec les mêmes informations que "Aujourd'hui"

##### Onglet "Semaine"

- Sélecteur de date (détermine la semaine)
- Vue hebdomadaire (lundi à dimanche)
- Chaque jour affiché dans une carte
- Mise en évidence du jour actuel (bordure bleue + chip "Aujourd'hui")
- Pour chaque jour :
  - Liste des pharmacies avec prochaine visite
  - Heure et nom de la pharmacie
  - Nom du commercial
  - Bouton pour voir les détails

**Logique de calcul** :
- Utilise la même logique que le tableau des pharmacies
- Priorité aux visites planifiées
- Sinon, utilise les `next_visit_date` des rapports
- Filtre par période selon l'onglet sélectionné

---

### 6. Module Factures

**Page** : `/invoices`

#### Fonctionnalités

##### Liste des factures

- Tableau avec onglets : Toutes, Payées, Impayées
- Colonnes : Numéro, Pharmacie, Montant, Date d'émission, Date d'échéance, Statut, Jours de retard
- Format de dates : dd/MM/yyyy
- Chips colorés pour les statuts
- Affichage des jours de retard si applicable

##### Détail d'une facture

- Informations complètes de la facture
- Dates formatées : dd/MM/yyyy
- Bouton "Envoyer par email" : Envoie la facture à l'email de la pharmacie
- Service email : Actuellement simulé (logs), prêt pour intégration réelle

---

### 7. Module Commerciaux

**Page** : `/users` (Admin uniquement)

#### Fonctionnalités

- **Liste des commerciaux** : Tableau avec nom, email, téléphone, rôle, statut
- **Création** : Formulaire pour créer un nouveau commercial
- **Modification** : Formulaire pré-rempli pour modifier un commercial
- **Suppression** : Bouton de suppression avec confirmation
- **Filtrage** : Récupération uniquement des utilisateurs avec rôle "commercial"

---

### 8. Module Supports Commerciaux

**Page** : `/materials`

#### Fonctionnalités

- Gestion des supports commerciaux (matériels, documents)
- CRUD complet pour les supports
- Association avec les pharmacies et visites

---

## Formats de données

### Format des dates

**Affichage** : `dd/MM/yyyy` (exemple : 25/12/2025)  
**Avec heure** : `dd/MM/yyyy HH:mm` (exemple : 25/12/2025 14:30)  
**Stockage** : ISO 8601 (exemple : 2025-12-25T14:30:00.000Z)  
**Champs HTML date** : `yyyy-MM-dd` (format requis par les inputs HTML)

### Modèles de données

#### Pharmacy (Pharmacie)

```json
{
  "id": "uuid",
  "name": "Nom de la pharmacie",
  "address": "Adresse complète",
  "city": "Ville",
  "postal_code": "Code postal",
  "pharmacist_name": "Nom du pharmacien",
  "pharmacist_email": "email@example.com",
  "pharmacist_phone": "Téléphone",
  "classification": "A|B|C",
  "commercial_id": "uuid du commercial assigné",
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

#### Visit (Visite)

```json
{
  "id": "uuid",
  "pharmacy_id": "uuid",
  "commercial_id": "uuid",
  "scheduled_date": "ISO date",
  "status": "planned|completed|cancelled|postponed",
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

#### VisitReport (Rapport de visite)

```json
{
  "id": "uuid",
  "visit_id": "uuid",
  "pharmacy_id": "uuid",
  "commercial_id": "uuid",
  "visit_date": "ISO date",
  "has_deposit": false,
  "bottles_deposited": 0,
  "stock_status": "good|low|out_of_stock|unknown",
  "display_stand_status": "in_place|not_in_place|unknown",
  "covering_status": "in_place|to_order|unknown",
  "covering_size_to_order": "string",
  "next_visit_date": "ISO date",
  "delivery_mode": "normal|deposit_sale",
  "notes": "string",
  "synced": false,
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

#### Invoice (Facture)

```json
{
  "id": "uuid",
  "pharmacy_id": "uuid",
  "invoice_number": "string",
  "amount": 0.0,
  "issue_date": "ISO date",
  "due_date": "ISO date",
  "payment_date": "ISO date",
  "status": "paid|unpaid|overdue",
  "days_overdue": 0,
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

#### User (Utilisateur)

```json
{
  "id": "uuid",
  "email": "email@example.com",
  "first_name": "Prénom",
  "last_name": "Nom",
  "role": "admin|commercial",
  "phone": "Téléphone",
  "is_active": true,
  "created_at": "ISO date",
  "updated_at": "ISO date"
}
```

---

## Rôles utilisateurs

### Admin

**Accès complet** :
- ✅ Voir toutes les pharmacies
- ✅ Créer, modifier, supprimer des pharmacies
- ✅ Gérer les commerciaux (CRUD)
- ✅ Voir toutes les visites
- ✅ Voir toutes les factures
- ✅ Accès au planning complet
- ✅ Gérer les supports commerciaux

**Restrictions** :
- ❌ Ne peut pas créer de rapports de visite (réservé aux commerciaux)
- ❌ Ne peut pas fixer les dates de prochaine visite (réservé aux commerciaux)

### Commercial

**Accès limité** :
- ✅ Voir uniquement ses pharmacies assignées
- ✅ Consulter les détails de ses pharmacies
- ✅ Voir les rapports de visite de ses pharmacies
- ✅ Voir les factures de ses pharmacies
- ✅ Fixer la date de la prochaine visite
- ✅ Créer des rapports de visite
- ✅ Accès au planning (filtré par ses pharmacies)

**Restrictions** :
- ❌ Ne peut pas modifier les pharmacies
- ❌ Ne peut pas créer de pharmacies
- ❌ Ne peut pas voir les autres commerciaux
- ❌ Ne peut pas voir les pharmacies non assignées

---

## Fonctionnalités techniques avancées

### Filtrage et tri

- **Tri multi-colonnes** : Tri possible sur toutes les colonnes du tableau pharmacies
- **Filtrage multi-critères** : Combinaison de plusieurs filtres simultanément
- **Recherche textuelle** : Insensible à la casse, recherche partielle
- **Performance** : Utilisation de `useMemo` pour optimiser les calculs

### Gestion des données

- **Enrichissement des données** : Combinaison de données de plusieurs sources (pharmacies, visites, rapports, utilisateurs)
- **Calculs dynamiques** : Calcul de la prochaine visite et dernière visite en temps réel
- **Optimisation** : Requêtes groupées pour réduire les appels API

### Interface utilisateur

- **Design responsive** : Adaptation aux différentes tailles d'écran
- **Feedback visuel** : Indicateurs de chargement, messages de succès/erreur
- **Navigation intuitive** : Menu latéral, breadcrumbs, boutons de retour
- **Accessibilité** : Tooltips, labels clairs, navigation au clavier

---

## Données de test

Le script `backend/scripts/init_data.py` génère des données de test :

- **50 pharmacies** : 25 à Paris, 25 à Marseille
- **3 commerciaux** : Odelia et Camille (Paris), Aaron (Marseille)
- **1 admin** : admin@digestic.fr
- **Visites planifiées** : Réparties entre les commerciaux
- **Rapports de visite** : Avec dates de prochaine visite
- **Factures** : Payées et impayées

---

## Points d'extension futurs

### Base de données
- Migration des fichiers JSON vers une base de données (PostgreSQL, MySQL, etc.)
- Les repositories sont déjà abstraits pour faciliter cette migration

### Authentification
- Ajout de mots de passe avec hachage
- Récupération de mot de passe
- Authentification à deux facteurs

### Email
- Intégration d'un service d'email réel (SMTP, SendGrid, etc.)
- Templates d'email pour les factures
- Notifications automatiques

### Fonctionnalités supplémentaires
- Export de données (PDF, Excel)
- Statistiques avancées et graphiques
- Géolocalisation des pharmacies
- Application mobile
- Mode hors ligne avec synchronisation

---

## Conclusion

L'application GRCP offre une solution complète pour la gestion des relations commerciales avec les pharmacies. Elle combine une architecture modulaire et extensible avec une interface utilisateur intuitive et des fonctionnalités adaptées aux besoins des administrateurs et des commerciaux.

La séparation claire entre les rôles, les fonctionnalités de filtrage et de tri avancées, ainsi que le système de planning intégré, font de cette application un outil efficace pour la gestion quotidienne des relations commerciales.

