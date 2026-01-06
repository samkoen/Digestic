"""
Script pour initialiser les données de test
Crée 50 pharmacies (25 à Paris, 25 à Marseille), 3 commerciaux,
des visites, rapports de visite, factures et bons de livraison
"""
import json
import os
import uuid
from datetime import datetime, timedelta
import random

# Chemins des fichiers
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
PHARMACIES_FILE = os.path.join(DATA_DIR, 'pharmacies.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
VISITS_FILE = os.path.join(DATA_DIR, 'visits.json')
VISIT_REPORTS_FILE = os.path.join(DATA_DIR, 'visit_reports.json')
INVOICES_FILE = os.path.join(DATA_DIR, 'invoices.json')
DELIVERY_NOTES_FILE = os.path.join(DATA_DIR, 'delivery_notes.json')

# Noms de pharmacies fictifs pour Paris
PARIS_PHARMACY_NAMES = [
    "Pharmacie du Louvre", "Pharmacie Centrale", "Pharmacie de la République",
    "Pharmacie Montmartre", "Pharmacie des Champs-Élysées", "Pharmacie Saint-Germain",
    "Pharmacie de la Bastille", "Pharmacie Marais", "Pharmacie Opéra",
    "Pharmacie Montparnasse", "Pharmacie Trocadéro", "Pharmacie Nation",
    "Pharmacie Belleville", "Pharmacie Pigalle", "Pharmacie Gare du Nord",
    "Pharmacie Gare de Lyon", "Pharmacie Châtelet", "Pharmacie Les Halles",
    "Pharmacie Latin Quarter", "Pharmacie Eiffel Tower", "Pharmacie Arc de Triomphe",
    "Pharmacie Notre-Dame", "Pharmacie Sacré-Cœur", "Pharmacie Père Lachaise",
    "Pharmacie Canal Saint-Martin"
]

# Noms de pharmacies fictifs pour Marseille
MARSEILLE_PHARMACY_NAMES = [
    "Pharmacie du Vieux-Port", "Pharmacie Canebière", "Pharmacie La Plaine",
    "Pharmacie Cours Julien", "Pharmacie Prado", "Pharmacie Corniche",
    "Pharmacie Castellane", "Pharmacie Noailles", "Pharmacie La Joliette",
    "Pharmacie Endoume", "Pharmacie Le Panier", "Pharmacie Saint-Charles",
    "Pharmacie La Timone", "Pharmacie Belle de Mai", "Pharmacie Belsunce",
    "Pharmacie La Major", "Pharmacie Mucem", "Pharmacie Friche",
    "Pharmacie Vallon des Auffes", "Pharmacie Malmousque", "Pharmacie Pointe Rouge",
    "Pharmacie Les Goudes", "Pharmacie Calanques", "Pharmacie Frioul",
    "Pharmacie Notre-Dame de la Garde"
]

# Adresses Paris (arrondissements variés)
PARIS_ADDRESSES = [
    ("1 Rue de Rivoli", "75001", "Paris"),
    ("15 Boulevard Haussmann", "75009", "Paris"),
    ("28 Place de la République", "75003", "Paris"),
    ("42 Rue Lepic", "75018", "Paris"),
    ("8 Avenue des Champs-Élysées", "75008", "Paris"),
    ("12 Boulevard Saint-Germain", "75005", "Paris"),
    ("25 Place de la Bastille", "75011", "Paris"),
    ("7 Rue des Rosiers", "75004", "Paris"),
    ("18 Boulevard des Capucines", "75002", "Paris"),
    ("33 Boulevard du Montparnasse", "75014", "Paris"),
    ("5 Place du Trocadéro", "75016", "Paris"),
    ("22 Place de la Nation", "75012", "Paris"),
    ("14 Rue de Belleville", "75020", "Paris"),
    ("30 Boulevard de Clichy", "75018", "Paris"),
    ("12 Boulevard de Denain", "75010", "Paris"),
    ("45 Boulevard Diderot", "75012", "Paris"),
    ("2 Rue de Rivoli", "75001", "Paris"),
    ("20 Rue Berger", "75001", "Paris"),
    ("8 Rue de la Sorbonne", "75005", "Paris"),
    ("15 Avenue Gustave Eiffel", "75007", "Paris"),
    ("28 Avenue des Champs-Élysées", "75008", "Paris"),
    ("5 Rue de la Cité", "75004", "Paris"),
    ("18 Rue du Chevalier de la Barre", "75018", "Paris"),
    ("12 Boulevard de Ménilmontant", "75020", "Paris"),
    ("25 Rue de la Roquette", "75011", "Paris"),
]

# Adresses Marseille
MARSEILLE_ADDRESSES = [
    ("10 Quai du Port", "13002", "Marseille"),
    ("25 La Canebière", "13001", "Marseille"),
    ("8 Place Jean Jaurès", "13001", "Marseille"),
    ("15 Cours Julien", "13006", "Marseille"),
    ("42 Avenue du Prado", "13008", "Marseille"),
    ("5 Corniche Kennedy", "13007", "Marseille"),
    ("18 Place Castellane", "13006", "Marseille"),
    ("12 Rue d'Aubagne", "13001", "Marseille"),
    ("30 Place de la Joliette", "13002", "Marseille"),
    ("7 Boulevard de la Plage", "13007", "Marseille"),
    ("22 Rue du Panier", "13002", "Marseille"),
    ("15 Boulevard Charles Nédelec", "13001", "Marseille"),
    ("28 Boulevard Baille", "13005", "Marseille"),
    ("5 Rue de la Belle de Mai", "13003", "Marseille"),
    ("18 Rue de la République", "13001", "Marseille"),
    ("12 Place de la Major", "13002", "Marseille"),
    ("25 Avenue du Mucem", "13002", "Marseille"),
    ("8 Rue de la Friche", "13003", "Marseille"),
    ("15 Chemin du Vallon des Auffes", "13007", "Marseille"),
    ("22 Rue de Malmousque", "13007", "Marseille"),
    ("30 Avenue de la Pointe Rouge", "13008", "Marseille"),
    ("5 Chemin des Goudes", "13008", "Marseille"),
    ("18 Route des Calanques", "13008", "Marseille"),
    ("12 Quai du Frioul", "13007", "Marseille"),
    ("25 Boulevard Notre-Dame", "13006", "Marseille"),
]

# Coordonnées approximatives
PARIS_COORDS = [
    (48.8606, 2.3376), (48.8720, 2.3310), (48.8676, 2.3631),
    (48.8867, 2.3431), (48.8698, 2.3086), (48.8534, 2.3488),
    (48.8532, 2.3697), (48.8566, 2.3622), (48.8702, 2.3319),
    (48.8422, 2.3219), (48.8630, 2.2878), (48.8485, 2.3700),
    (48.8720, 2.3844), (48.8827, 2.3376), (48.8809, 2.3553),
    (48.8447, 2.3732), (48.8606, 2.3376), (48.8606, 2.3431),
    (48.8506, 2.3442), (48.8584, 2.2945), (48.8738, 2.2950),
    (48.8530, 2.3499), (48.8867, 2.3431), (48.8614, 2.3883),
    (48.8700, 2.3680),
]

MARSEILLE_COORDS = [
    (43.2965, 5.3698), (43.2965, 5.3811), (43.3000, 5.3800),
    (43.2900, 5.3800), (43.2700, 5.3800), (43.2600, 5.3800),
    (43.2800, 5.3900), (43.2950, 5.3750), (43.3050, 5.3650),
    (43.2850, 5.3700), (43.3000, 5.3700), (43.2900, 5.3850),
    (43.2750, 5.4000), (43.3100, 5.3800), (43.2950, 5.3750),
    (43.3000, 5.3650), (43.2950, 5.3650), (43.3100, 5.3800),
    (43.2800, 5.3600), (43.2800, 5.3600), (43.2500, 5.3800),
    (43.2400, 5.3800), (43.2300, 5.3800), (43.2800, 5.3500),
    (43.2800, 5.3900),
]

# Noms de pharmaciens fictifs
PHARMACIST_FIRST_NAMES = ["Jean", "Marie", "Pierre", "Sophie", "Luc", "Claire", "Antoine", "Julie", "Thomas", "Camille"]
PHARMACIST_LAST_NAMES = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Petit", "Durand", "Leroy", "Moreau", "Simon"]

def generate_users():
    """Génère les utilisateurs commerciaux et admin"""
    now = datetime.now().isoformat()
    
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@digestic.fr",
            "first_name": "Admin",
            "last_name": "Digestic",
            "role": "admin",
            "phone": "0612345677",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "email": "odelia@digestic.fr",
            "first_name": "Odelia",
            "last_name": "Martin",
            "role": "commercial",
            "phone": "0612345678",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "email": "camille@digestic.fr",
            "first_name": "Camille",
            "last_name": "Dubois",
            "role": "commercial",
            "phone": "0612345679",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "email": "aaron@digestic.fr",
            "first_name": "Aaron",
            "last_name": "Bernard",
            "role": "commercial",
            "phone": "0612345680",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
    ]
    
    return users

def generate_pharmacies(users):
    """Génère les pharmacies avec répartition par commercial"""
    pharmacies = []
    now = datetime.now().isoformat()
    
    # Identifier les commerciaux (exclure l'admin qui est le premier)
    # users[0] est l'admin, users[1] est Odelia, users[2] est Camille, users[3] est Aaron
    odelia_id = users[1]["id"]  # Premier commercial (Odelia)
    camille_id = users[2]["id"]  # Deuxième commercial (Camille)
    aaron_id = users[3]["id"]  # Troisième commercial (Aaron)
    
    # Pharmacies Paris - réparties entre Odelia (12) et Camille (13)
    for i, name in enumerate(PARIS_PHARMACY_NAMES):
        address, postal_code, city = PARIS_ADDRESSES[i]
        lat, lon = PARIS_COORDS[i]
        first_name = PHARMACIST_FIRST_NAMES[i % len(PHARMACIST_FIRST_NAMES)]
        last_name = PHARMACIST_LAST_NAMES[i % len(PHARMACIST_LAST_NAMES)]
        
        # Classification aléatoire (plus de A à Paris)
        classification = "A" if i < 8 else ("B" if i < 18 else "C")
        
        # Répartition: Odelia pour les 12 premières, Camille pour les 13 suivantes
        commercial_id = odelia_id if i < 12 else camille_id
        
        pharmacy = {
            "id": str(uuid.uuid4()),
            "name": name,
            "address": address,
            "city": city,
            "postal_code": postal_code,
            "latitude": lat,
            "longitude": lon,
            "pharmacist_name": f"{first_name} {last_name}",
            "pharmacist_email": f"{first_name.lower()}.{last_name.lower()}@{name.lower().replace(' ', '').replace('-', '')}.fr",
            "pharmacist_phone": f"01{40 + i:02d}{i*1000:04d}",
            "classification": classification,
            "commercial_id": commercial_id,  # Ajout du commercial assigné
            "created_at": now,
            "updated_at": now
        }
        pharmacies.append(pharmacy)
    
    # Pharmacies Marseille - toutes à Aaron
    for i, name in enumerate(MARSEILLE_PHARMACY_NAMES):
        address, postal_code, city = MARSEILLE_ADDRESSES[i]
        lat, lon = MARSEILLE_COORDS[i]
        first_name = PHARMACIST_FIRST_NAMES[i % len(PHARMACIST_FIRST_NAMES)]
        last_name = PHARMACIST_LAST_NAMES[i % len(PHARMACIST_LAST_NAMES)]
        
        # Classification aléatoire
        classification = "A" if i < 5 else ("B" if i < 15 else "C")
        
        pharmacy = {
            "id": str(uuid.uuid4()),
            "name": name,
            "address": address,
            "city": city,
            "postal_code": postal_code,
            "latitude": lat,
            "longitude": lon,
            "pharmacist_name": f"{first_name} {last_name}",
            "pharmacist_email": f"{first_name.lower()}.{last_name.lower()}@{name.lower().replace(' ', '').replace('-', '')}.fr",
            "pharmacist_phone": f"04{91 + i:02d}{i*1000:04d}",
            "classification": classification,
            "commercial_id": aaron_id,  # Toutes les pharmacies de Marseille à Aaron
            "created_at": now,
            "updated_at": now
        }
        pharmacies.append(pharmacy)
    
    return pharmacies

def generate_visits(pharmacies, users):
    """Génère des visites planifiées et complétées"""
    visits = []
    now = datetime.now()
    
    # Créer des visites sur les 3 derniers mois
    for i in range(60):  # 60 visites au total
        pharmacy = random.choice(pharmacies)
        commercial_id = pharmacy.get("commercial_id", random.choice([u["id"] for u in users]))
        
        # Date aléatoire dans les 3 derniers mois
        days_ago = random.randint(0, 90)
        visit_date = now - timedelta(days=days_ago)
        
        # 70% complétées, 20% planifiées, 10% annulées
        rand = random.random()
        if rand < 0.7:
            status = "completed"
        elif rand < 0.9:
            status = "planned"
        else:
            status = "cancelled"
        
        visit = {
            "id": str(uuid.uuid4()),
            "pharmacy_id": pharmacy["id"],
            "commercial_id": commercial_id,
            "scheduled_date": visit_date.isoformat(),
            "scheduled_time": f"{random.randint(9, 17):02d}:00",
            "status": status,
            "notes": None,
            "created_at": (visit_date - timedelta(days=random.randint(1, 7))).isoformat(),
            "updated_at": visit_date.isoformat()
        }
        visits.append(visit)
    
    return visits

def generate_visit_reports(visits, pharmacies):
    """Génère des rapports de visite pour les visites complétées"""
    reports = []
    stock_statuses = ["good", "low", "out_of_stock", "unknown"]
    display_statuses = ["in_place", "not_in_place", "unknown"]
    covering_statuses = ["in_place", "to_order", "unknown"]
    covering_sizes = ["S", "M", "L", "XL"]
    
    completed_visits = [v for v in visits if v["status"] == "completed"]
    
    for visit in completed_visits[:40]:  # 40 rapports sur les visites complétées
        pharmacy = next((p for p in pharmacies if p["id"] == visit["pharmacy_id"]), None)
        if not pharmacy:
            continue
        
        has_deposit = random.random() < 0.6  # 60% avec dépôt
        bottles = random.randint(5, 50) if has_deposit else 0
        
        visit_date = datetime.fromisoformat(visit["scheduled_date"])
        next_visit_date = visit_date + timedelta(days=random.randint(15, 45))
        
        report = {
            "id": str(uuid.uuid4()),
            "visit_id": visit["id"],
            "pharmacy_id": visit["pharmacy_id"],
            "commercial_id": visit["commercial_id"],
            "visit_date": visit_date.isoformat(),
            "has_deposit": has_deposit,
            "bottles_deposited": bottles,
            "stock_status": random.choice(stock_statuses),
            "display_stand_status": random.choice(display_statuses),
            "covering_status": random.choice(covering_statuses),
            "covering_size_to_order": random.choice(covering_sizes) if random.random() < 0.3 else None,
            "next_visit_date": next_visit_date.isoformat(),
            "delivery_mode": "deposit_sale" if random.random() < 0.2 else "normal",
            "notes": f"Visite productive. {random.choice(['Client satisfait', 'Demande de réassort', 'Nouveau contact', 'Suivi nécessaire'])}",
            "synced": True,
            "created_at": visit_date.isoformat(),
            "updated_at": visit_date.isoformat()
        }
        reports.append(report)
    
    return reports

def generate_delivery_notes(visit_reports):
    """Génère des bons de livraison pour les rapports avec dépôt"""
    delivery_notes = []
    
    for report in visit_reports:
        if report["has_deposit"] and report["bottles_deposited"] > 0:
            visit_date = datetime.fromisoformat(report["visit_date"])
            
            note = {
                "id": str(uuid.uuid4()),
                "visit_report_id": report["id"],
                "pharmacy_id": report["pharmacy_id"],
                "commercial_id": report["commercial_id"],
                "delivery_date": visit_date.isoformat(),
                "bottles_count": report["bottles_deposited"],
                "is_deposit_sale": report["delivery_mode"] == "deposit_sale",
                "status": "sent" if random.random() < 0.8 else "pending",
                "sage_reference": f"BL-{random.randint(1000, 9999)}" if random.random() < 0.5 else None,
                "email_sent": random.random() < 0.7,
                "email_sent_at": (visit_date + timedelta(hours=2)).isoformat() if random.random() < 0.7 else None,
                "created_at": visit_date.isoformat(),
                "updated_at": visit_date.isoformat()
            }
            delivery_notes.append(note)
    
    return delivery_notes

def generate_invoices(pharmacies):
    """Génère des factures (payées et impayées)"""
    invoices = []
    now = datetime.now()
    
    # Générer 2-3 factures par pharmacie
    for pharmacy in pharmacies:
        num_invoices = random.randint(2, 3)
        
        for i in range(num_invoices):
            # Date d'émission dans les 6 derniers mois
            days_ago = random.randint(30, 180)
            issue_date = now - timedelta(days=days_ago)
            due_date = issue_date + timedelta(days=30)
            
            amount = round(random.uniform(150.0, 1500.0), 2)
            
            # 60% payées, 25% en attente, 15% en retard
            rand = random.random()
            if rand < 0.6:
                status = "paid"
                payment_date = due_date + timedelta(days=random.randint(-5, 10))
                days_overdue = 0
            elif rand < 0.85:
                status = "pending"
                payment_date = None
                days_overdue = max(0, (now - due_date).days)
            else:
                status = "overdue"
                payment_date = None
                days_overdue = max(0, (now - due_date).days)
            
            invoice = {
                "id": str(uuid.uuid4()),
                "pharmacy_id": pharmacy["id"],
                "invoice_number": f"FAC-{pharmacy['name'][:3].upper()}-{random.randint(1000, 9999)}",
                "amount": amount,
                "issue_date": issue_date.isoformat(),
                "due_date": due_date.isoformat(),
                "status": status,
                "payment_date": payment_date.isoformat() if payment_date else None,
                "sage_reference": f"SAGE-{random.randint(10000, 99999)}" if random.random() < 0.7 else None,
                "days_overdue": days_overdue,
                "created_at": issue_date.isoformat(),
                "updated_at": now.isoformat()
            }
            invoices.append(invoice)
    
    return invoices

def main():
    """Fonction principale"""
    # Créer le dossier data s'il n'existe pas
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("Generation des donnees...")
    
    # Générer les utilisateurs d'abord
    users = generate_users()
    print(f"{len(users)} commerciaux crees")
    
    # Générer les pharmacies avec répartition
    pharmacies = generate_pharmacies(users)
    print(f"{len(pharmacies)} pharmacies creees")
    print(f"   - {len([p for p in pharmacies if p.get('commercial_id') == users[0]['id']])} pharmacies pour Odelia (Paris)")
    print(f"   - {len([p for p in pharmacies if p.get('commercial_id') == users[1]['id']])} pharmacies pour Camille (Paris)")
    print(f"   - {len([p for p in pharmacies if p.get('commercial_id') == users[2]['id']])} pharmacies pour Aaron (Marseille)")
    
    # Générer les visites
    visits = generate_visits(pharmacies, users)
    print(f"{len(visits)} visites creees")
    
    # Générer les rapports de visite
    visit_reports = generate_visit_reports(visits, pharmacies)
    print(f"{len(visit_reports)} rapports de visite crees")
    
    # Générer les bons de livraison
    delivery_notes = generate_delivery_notes(visit_reports)
    print(f"{len(delivery_notes)} bons de livraison crees")
    
    # Générer les factures
    invoices = generate_invoices(pharmacies)
    paid = len([inv for inv in invoices if inv["status"] == "paid"])
    pending = len([inv for inv in invoices if inv["status"] == "pending"])
    overdue = len([inv for inv in invoices if inv["status"] == "overdue"])
    print(f"{len(invoices)} factures creees ({paid} payees, {pending} en attente, {overdue} en retard)")
    
    # Sauvegarder toutes les données
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    with open(PHARMACIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)
    
    with open(VISITS_FILE, 'w', encoding='utf-8') as f:
        json.dump(visits, f, ensure_ascii=False, indent=2)
    
    with open(VISIT_REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(visit_reports, f, ensure_ascii=False, indent=2)
    
    with open(DELIVERY_NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(delivery_notes, f, ensure_ascii=False, indent=2)
    
    with open(INVOICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, ensure_ascii=False, indent=2)
    
    print(f"\nToutes les donnees ont ete sauvegardees dans: {DATA_DIR}")

if __name__ == "__main__":
    main()
