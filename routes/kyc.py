# routes/kyc.py
from flask import Blueprint, request, jsonify, current_app
from middleware.auth import jwt_required
from extensions import db
from models import User, KYC, AuditLog
from services.kyc_service import submit_kyc, get_kyc_status, approve_kyc, reject_kyc
from services.notification_service import create_notification
from datetime import datetime
from utils.email_service import send_kyc_status_email

from routes.admin import admin_bp, admin_required  # ← Ajouter cet import
import os

kyc_bp = Blueprint('kyc', __name__)


@kyc_bp.route('/submit', methods=['POST'])
@jwt_required
def submit_kyc_documents():
    """Soumettre les documents KYC"""
    data = request.json
    document_type = data.get('document_type')
    document_number = data.get('document_number')
    document_image = data.get('document_image')
    selfie_image = data.get('selfie_image')

    # Validations
    if not document_type or not document_number or not document_image or not selfie_image:
        return jsonify({'error': 'All KYC fields are required'}), 400

    allowed_types = ['cin', 'passport', 'driver_license']
    if document_type not in allowed_types:
        return jsonify({'error': f'Invalid document type. Allowed: {allowed_types}'}), 400

    # Soumettre KYC
    try:
        kyc = submit_kyc(
            user_id=request.user_id,
            document_type=document_type,
            document_number=document_number,
            document_image=document_image,
            selfie_image=selfie_image
        )

        # Audit
        audit = AuditLog(
            user_id=request.user_id,
            action='kyc_submitted',
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()

        return jsonify({
            'message': 'KYC documents submitted successfully',
            'status': 'pending',
            'submitted_at': kyc.submitted_at.isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@kyc_bp.route('/status', methods=['GET'])
@jwt_required
def check_kyc_status():
    """Vérifier le statut KYC"""
    status = get_kyc_status(request.user_id)
    return jsonify(status), 200


@kyc_bp.route('/upload-image', methods=['POST'])
@jwt_required
def upload_kyc_image():
    """Uploader une image KYC"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    image_type = request.form.get('type', 'document')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Vérifier extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': 'Invalid file type'}), 400

    # Sauvegarder
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"kyc_{request.user_id}_{image_type}_{timestamp}.{file.filename.rsplit('.', 1)[1].lower()}"

    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'kyc')
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return jsonify({
        'message': 'Image uploaded successfully',
        'image_url': f"/uploads/kyc/{filename}",
        'type': image_type
    }), 200


# Routes Admin
@kyc_bp.route('/admin/pending', methods=['GET'])
@jwt_required
def admin_pending_kyc():
    """Admin: Voir les demandes KYC en attente"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    pending_kyc = KYC.query.filter_by(status='pending').order_by(KYC.submitted_at.asc()).all()

    return jsonify({
        'pending_kyc': [{
            'id': k.id,
            'user_id': k.user_id,
            'user_email': User.query.get(k.user_id).email if k.user_id else None,
            'user_name': f"{User.query.get(k.user_id).first_name} {User.query.get(k.user_id).last_name}" if k.user_id else None,
            'document_type': k.document_type,
            'document_number': k.document_number,
            'document_image': k.document_image,
            'selfie_image': k.selfie_image,
            'submitted_at': k.submitted_at.isoformat()
        } for k in pending_kyc]
    }), 200


@kyc_bp.route('/admin/<int:kyc_id>/approve', methods=['POST'])
@jwt_required
def admin_approve_kyc(kyc_id):
    """Admin: Approuver une demande KYC"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    data = request.json or {}
    admin_id = request.user_id

    kyc = approve_kyc(kyc_id, admin_id)

    if not kyc:
        return jsonify({'error': 'KYC request not found'}), 404

    # Notification à l'utilisateur
    if kyc.user_id:
        create_notification(
            kyc.user_id,
            "KYC Approuvé",
            "Votre vérification d'identité a été approuvée. Vous pouvez maintenant créer des cartes virtuelles."
        )

    return jsonify({
        'message': 'KYC approved successfully',
        'user_id': kyc.user_id,
        'status': kyc.status
    }), 200


@kyc_bp.route('/admin/<int:kyc_id>/reject', methods=['POST'])
@jwt_required
def admin_reject_kyc(kyc_id):
    """Admin: Rejeter une demande KYC"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    data = request.json
    reason = data.get('reason', 'Documents non conformes')
    admin_id = request.user_id

    kyc = reject_kyc(kyc_id, admin_id, reason)

    if not kyc:
        return jsonify({'error': 'KYC request not found'}), 404

    # Notification à l'utilisateur
    if kyc.user_id:
        create_notification(
            kyc.user_id,
            "KYC Rejeté",
            f"Votre vérification d'identité a été rejetée. Raison: {reason}"
        )

    return jsonify({
        'message': 'KYC rejected',
        'user_id': kyc.user_id,
        'status': kyc.status,
        'reason': reason
    }), 200


@kyc_bp.route('/admin/<int:user_id>/reset', methods=['POST'])
@jwt_required
def admin_reset_kyc(user_id):
    """Admin: Réinitialiser le statut KYC d'un utilisateur"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    kyc = KYC.query.filter_by(user_id=user_id).first()

    if not kyc:
        return jsonify({'error': 'No KYC found for this user'}), 404

    kyc.status = 'pending'
    kyc.rejection_reason = None
    kyc.reviewed_at = None
    db.session.commit()

    return jsonify({
        'message': 'KYC status reset to pending',
        'user_id': user_id
    }), 200


@admin_bp.route('/kyc/<int:kyc_id>/approve', methods=['POST'])
@jwt_required
@admin_required
def admin_approve_kyc(kyc_id):
    """Admin: Approuver KYC"""
    from models import KYC

    kyc = KYC.query.get(kyc_id)

    if not kyc:
        return jsonify({'error': 'KYC not found'}), 404

    kyc.status = 'approved'
    kyc.reviewed_at = datetime.utcnow()

    user = User.query.get(kyc.user_id)
    user.is_verified = True

    db.session.commit()

    # 📧 ENVOYER EMAIL DE CONFIRMATION
    send_kyc_status_email(user, 'approved')

    return jsonify({
        'message': 'KYC approved',
        'user_id': user.id,
        'is_verified': user.is_verified
    }), 200