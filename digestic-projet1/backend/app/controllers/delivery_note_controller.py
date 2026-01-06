from flask import Blueprint, request, jsonify
from app.services.delivery_note_service import DeliveryNoteService
from app.repositories.delivery_note_repository import DeliveryNoteRepository

delivery_note_bp = Blueprint('delivery_note', __name__)

def get_delivery_note_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    repository = DeliveryNoteRepository(data_dir)
    return DeliveryNoteService(repository)

@delivery_note_bp.route('', methods=['GET'])
def get_delivery_notes():
    """Récupère tous les bons de livraison"""
    try:
        service = get_delivery_note_service()
        pharmacy_id = request.args.get('pharmacy_id')
        
        if pharmacy_id:
            notes = service.get_delivery_notes_by_pharmacy(pharmacy_id)
        else:
            notes = service.get_all_delivery_notes()
        
        return jsonify([note.to_dict() for note in notes]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@delivery_note_bp.route('/<note_id>', methods=['GET'])
def get_delivery_note(note_id):
    """Récupère un bon de livraison par son ID"""
    try:
        service = get_delivery_note_service()
        note = service.get_delivery_note_by_id(note_id)
        
        if not note:
            return jsonify({'error': 'Bon de livraison non trouvé'}), 404
        
        return jsonify(note.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@delivery_note_bp.route('', methods=['POST'])
def create_delivery_note():
    """Crée un nouveau bon de livraison"""
    try:
        data = request.get_json()
        service = get_delivery_note_service()
        note = service.create_delivery_note(data)
        return jsonify(note.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@delivery_note_bp.route('/<note_id>/send', methods=['POST'])
def send_delivery_note(note_id):
    """Marque un bon de livraison comme envoyé"""
    try:
        service = get_delivery_note_service()
        note = service.mark_as_sent(note_id)
        
        if not note:
            return jsonify({'error': 'Bon de livraison non trouvé'}), 404
        
        return jsonify(note.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


