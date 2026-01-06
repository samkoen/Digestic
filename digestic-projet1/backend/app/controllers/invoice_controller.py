from flask import Blueprint, request, jsonify
from app.services.invoice_service import InvoiceService
from app.repositories.invoice_repository import InvoiceRepository

invoice_bp = Blueprint('invoice', __name__)

def get_invoice_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    repository = InvoiceRepository(data_dir)
    return InvoiceService(repository)

@invoice_bp.route('', methods=['GET'])
def get_invoices():
    """Récupère toutes les factures"""
    try:
        service = get_invoice_service()
        pharmacy_id = request.args.get('pharmacy_id')
        overdue = request.args.get('overdue', 'false').lower() == 'true'
        days = int(request.args.get('days', 30))
        
        if overdue:
            invoices = service.get_overdue_invoices(days)
        elif pharmacy_id:
            invoices = service.get_invoices_by_pharmacy(pharmacy_id)
        else:
            invoices = service.get_all_invoices()
        
        return jsonify([invoice.to_dict() for invoice in invoices]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Récupère une facture par son ID"""
    try:
        service = get_invoice_service()
        invoice = service.get_invoice_by_id(invoice_id)
        
        if not invoice:
            return jsonify({'error': 'Facture non trouvée'}), 404
        
        return jsonify(invoice.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('', methods=['POST'])
def create_invoice():
    """Crée une nouvelle facture"""
    try:
        data = request.get_json()
        service = get_invoice_service()
        invoice = service.create_invoice(data)
        return jsonify(invoice.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@invoice_bp.route('/<invoice_id>', methods=['PUT'])
def update_invoice(invoice_id):
    """Met à jour une facture"""
    try:
        data = request.get_json()
        service = get_invoice_service()
        invoice = service.update_invoice(invoice_id, data)
        
        if not invoice:
            return jsonify({'error': 'Facture non trouvée'}), 404
        
        return jsonify(invoice.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@invoice_bp.route('/<invoice_id>/send-email', methods=['POST'])
def send_invoice_email(invoice_id):
    """Envoie une facture par email à la pharmacie"""
    try:
        from app.services.email_service import EmailService
        from app.repositories.pharmacy_repository import PharmacyRepository
        from flask import current_app
        
        # Récupérer la facture
        service = get_invoice_service()
        invoice = service.get_invoice_by_id(invoice_id)
        
        if not invoice:
            return jsonify({'error': 'Facture non trouvée'}), 404
        
        # Récupérer la pharmacie pour obtenir l'email
        data_dir = current_app.config.get('DATA_DIR', 'data')
        pharmacy_repo = PharmacyRepository(data_dir)
        pharmacy = pharmacy_repo.find_by_id(invoice.pharmacy_id)
        
        if not pharmacy:
            return jsonify({'error': 'Pharmacie non trouvée'}), 404
        
        if not pharmacy.pharmacist_email:
            return jsonify({'error': 'Aucun email enregistré pour cette pharmacie'}), 400
        
        # Envoyer l'email
        email_service = EmailService()
        success = email_service.send_invoice_email(
            to_email=pharmacy.pharmacist_email,
            pharmacy_name=pharmacy.name,
            invoice_number=invoice.invoice_number,
            invoice_amount=invoice.amount,
            invoice_date=invoice.issue_date
        )
        
        if success:
            return jsonify({
                'message': f'Facture envoyée avec succès à {pharmacy.pharmacist_email}',
                'email': pharmacy.pharmacist_email
            }), 200
        else:
            return jsonify({'error': 'Erreur lors de l\'envoi de l\'email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

