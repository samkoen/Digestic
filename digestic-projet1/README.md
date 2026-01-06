# Plateforme de Gestion de la Relation Commerciale Pharmacie (GRCP)

Application web pour la gestion de la relation commerciale entre MT2N Digestic et ses pharmacies partenaires.

## Structure du Projet

```
.
├── backend/          # Application Flask (Backend)
│   ├── app/
│   │   ├── models/          # Modèles de données
│   │   ├── repositories/    # Gestion des données (fichiers JSON)
│   │   ├── services/        # Logique métier
│   │   ├── business/         # Couche métier avancée
│   │   ├── controllers/     # Routes API
│   │   └── __init__.py
│   ├── data/                # Fichiers JSON de données
│   ├── run.py
│   └── requirements.txt
│
└── frontend/        # Application React (Frontend)
    ├── src/
    │   ├── components/      # Composants réutilisables
    │   ├── pages/          # Pages de l'application
    │   ├── services/       # Services API
    │   └── App.jsx
    ├── package.json
    └── vite.config.js
```

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Le serveur backend sera accessible sur `http://localhost:5000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le serveur frontend sera accessible sur `http://localhost:3000`

## Fonctionnalités

### Backend

- **Modèles de données** : Pharmacy, Visit, VisitReport, DeliveryNote, Invoice, User, CommercialMaterial
- **Repositories** : Gestion des données via fichiers JSON (facilement remplaçable par une base de données)
- **Services** : Logique métier pour chaque entité
- **Business Layer** : Optimisation d'itinéraires, suggestions de dates de visite
- **Controllers** : API RESTful pour toutes les entités

### Frontend

- **Tableau de bord** : Vue d'ensemble des statistiques
- **Gestion des pharmacies** : Liste, création, modification, détails
- **Gestion des visites** : Planification et suivi
- **Rapports de visite** : Saisie complète des rapports
- **Factures** : Consultation et suivi des factures
- **Supports commerciaux** : Catalogue numérique

## Architecture

L'application suit une architecture en couches :

1. **Controllers** : Gèrent les requêtes HTTP et les réponses
2. **Services** : Contiennent la logique métier
3. **Business** : Logique métier avancée (optimisation, calculs)
4. **Repositories** : Abstraction de l'accès aux données
5. **Models** : Structures de données

Cette architecture permet de facilement remplacer les fichiers JSON par une vraie base de données (PostgreSQL) plus tard.

## Prochaines étapes

- Intégration avec Sage (API)
- Migration vers PostgreSQL
- Application mobile React Native
- Authentification et gestion des utilisateurs
- Envoi d'emails automatiques


