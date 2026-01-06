from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])  # Permet les requêtes cross-origin avec credentials
    
    # Configuration
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # False pour le développement local
    import os
    # Chemin relatif au dossier backend (quand on lance depuis backend/)
    # __file__ est backend/app/__init__.py, donc on remonte d'un niveau pour avoir backend/
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    app.config['DATA_DIR'] = os.path.join(backend_dir, 'data')
    
    # Enregistrement des blueprints
    from app.controllers.auth_controller import auth_bp
    from app.controllers.pharmacy_controller import pharmacy_bp
    from app.controllers.visit_controller import visit_bp
    from app.controllers.visit_report_controller import visit_report_bp
    from app.controllers.delivery_note_controller import delivery_note_bp
    from app.controllers.invoice_controller import invoice_bp
    from app.controllers.commercial_material_controller import commercial_material_bp
    from app.controllers.user_controller import user_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(pharmacy_bp, url_prefix='/api/pharmacies')
    app.register_blueprint(visit_bp, url_prefix='/api/visits')
    app.register_blueprint(visit_report_bp, url_prefix='/api/visit-reports')
    app.register_blueprint(delivery_note_bp, url_prefix='/api/delivery-notes')
    app.register_blueprint(invoice_bp, url_prefix='/api/invoices')
    app.register_blueprint(commercial_material_bp, url_prefix='/api/commercial-materials')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    
    return app

