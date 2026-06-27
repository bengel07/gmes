# services/kyc_service.py
from extensions import db
from models import KYC, User
from datetime import datetime


def submit_kyc(user_id, document_type, document_number, document_image, selfie_image):
    """Soumettre une demande KYC"""
    # Vérifier si l'utilisateur a déjà soumis
    existing = KYC.query.filter_by(user_id=user_id).first()

    if existing:
        existing.document_type = document_type
        existing.document_number = document_number
        existing.document_image = document_image
        existing.selfie_image = selfie_image
        existing.status = 'pending'
        existing.submitted_at = datetime.utcnow()
        existing.rejection_reason = None
        kyc = existing
    else:
        kyc = KYC(
            user_id=user_id,
            document_type=document_type,
            document_number=document_number,
            document_image=document_image,
            selfie_image=selfie_image,
            status='pending'
        )
        db.session.add(kyc)

    db.session.commit()
    return kyc


def approve_kyc(kyc_id, admin_id):
    """Approuver une demande KYC"""
    kyc = KYC.query.get(kyc_id)
    if not kyc:
        return None

    kyc.status = 'approved'
    kyc.reviewed_at = datetime.utcnow()

    # Marquer l'utilisateur comme vérifié
    user = User.query.get(kyc.user_id)
    if user:
        user.is_verified = True

    db.session.commit()
    return kyc


def reject_kyc(kyc_id, admin_id, reason):
    """Rejeter une demande KYC"""
    kyc = KYC.query.get(kyc_id)
    if not kyc:
        return None

    kyc.status = 'rejected'
    kyc.rejection_reason = reason
    kyc.reviewed_at = datetime.utcnow()

    db.session.commit()
    return kyc


def get_kyc_status(user_id):
    """Obtenir le statut KYC d'un utilisateur"""
    kyc = KYC.query.filter_by(user_id=user_id).first()

    if not kyc:
        return {'status': 'not_submitted'}

    return {
        'status': kyc.status,
        'document_type': kyc.document_type,
        'submitted_at': kyc.submitted_at.isoformat() if kyc.submitted_at else None,
        'reviewed_at': kyc.reviewed_at.isoformat() if kyc.reviewed_at else None,
        'rejection_reason': kyc.rejection_reason
    }