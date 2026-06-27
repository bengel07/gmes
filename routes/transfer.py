# routes/transfer.py
from flask import Blueprint, request, jsonify
from middleware.auth import jwt_required
from extensions import db
from models import User, Wallet, Transaction, AuditLog, Notification
from services.notification_service import create_notification
from utils.helpers import generate_reference
from datetime import datetime

transfer_bp = Blueprint('transfer', __name__)


@transfer_bp.route('/send', methods=['POST'])
@jwt_required
def send_money():
    """Envoyer de l'argent à un autre utilisateur GmesPay"""
    data = request.json
    recipient_email = data.get('recipient_email')
    recipient_phone = data.get('recipient_phone')
    amount = data.get('amount')
    currency = data.get('currency', 'HTG')  # HTG or USD
    description = data.get('description', '')

    # Validation
    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400

    if not recipient_email and not recipient_phone:
        return jsonify({'error': 'Recipient email or phone required'}), 400

    # Trouver le destinataire
    recipient = None
    if recipient_email:
        recipient = User.query.filter_by(email=recipient_email).first()
    elif recipient_phone:
        recipient = User.query.filter_by(phone=recipient_phone).first()

    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    if recipient.id == request.user_id:
        return jsonify({'error': 'Cannot send money to yourself'}), 400

    # Vérifier le solde
    sender_wallet = Wallet.query.filter_by(user_id=request.user_id).first()

    if currency == 'HTG':
        if not sender_wallet or sender_wallet.balance_htg < amount:
            return jsonify({'error': 'Insufficient HTG balance'}), 400
    else:  # USD
        if not sender_wallet or sender_wallet.balance_usd < amount:
            return jsonify({'error': 'Insufficient USD balance'}), 400

    # Calculer les frais (1% pour transfert interne)
    fee = amount * 0.01
    net_amount = amount - fee

    # Wallet du destinataire
    recipient_wallet = Wallet.query.filter_by(user_id=recipient.id).first()
    if not recipient_wallet:
        return jsonify({'error': 'Recipient wallet not found'}), 404

    # Effectuer le transfert
    reference = generate_reference('TRF')

    if currency == 'HTG':
        sender_wallet.balance_htg -= amount
        recipient_wallet.balance_htg += net_amount
    else:
        sender_wallet.balance_usd -= amount
        recipient_wallet.balance_usd += net_amount

    sender_wallet.updated_at = datetime.utcnow()
    recipient_wallet.updated_at = datetime.utcnow()

    # Transaction pour l'expéditeur
    sender_transaction = Transaction(
        user_id=request.user_id,
        wallet_id=sender_wallet.id,
        type='transfer_sent',
        amount=amount,
        fee=fee,
        currency=currency,
        status='completed',
        reference=reference,
        description=f"Transfer to {recipient.email} - {description}" if description else f"Transfer to {recipient.email}"
    )
    db.session.add(sender_transaction)

    # Transaction pour le destinataire
    recipient_transaction = Transaction(
        user_id=recipient.id,
        wallet_id=recipient_wallet.id,
        type='transfer_received',
        amount=net_amount,
        fee=0,
        currency=currency,
        status='completed',
        reference=reference,
        description=f"Transfer from {sender_wallet.user.email}" if hasattr(sender_wallet,
                                                                           'user') else "Transfer received"
    )
    db.session.add(recipient_transaction)

    # Audit log
    audit = AuditLog(
        user_id=request.user_id,
        action=f'transfer_sent_{currency}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(audit)

    # Notification pour le destinataire
    create_notification(
        recipient.id,
        "Transfert reçu",
        f"Vous avez reçu {net_amount} {currency} de {sender_wallet.user.email if hasattr(sender_wallet, 'user') else 'un utilisateur'}"
    )

    db.session.commit()

    return jsonify({
        'message': 'Transfer completed successfully',
        'reference': reference,
        'amount': amount,
        'fee': fee,
        'net_amount': net_amount,
        'currency': currency,
        'recipient': recipient.email,
        'new_balance': float(sender_wallet.balance_htg if currency == 'HTG' else sender_wallet.balance_usd)
    }), 200


@transfer_bp.route('/history', methods=['GET'])
@jwt_required
def transfer_history():
    """Historique des transferts (envoyés et reçus)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Transferts envoyés
    sent_transfers = Transaction.query.filter_by(
        user_id=request.user_id,
        type='transfer_sent'
    ).order_by(Transaction.created_at.desc())

    # Transferts reçus
    received_transfers = Transaction.query.filter_by(
        user_id=request.user_id,
        type='transfer_received'
    ).order_by(Transaction.created_at.desc())

    sent_paginated = sent_transfers.paginate(page=page, per_page=per_page)
    received_paginated = received_transfers.paginate(page=page, per_page=per_page)

    return jsonify({
        'sent': [{
            'id': t.id,
            'amount': float(t.amount),
            'fee': float(t.fee),
            'net_amount': float(t.amount - t.fee),
            'currency': t.currency,
            'reference': t.reference,
            'description': t.description,
            'status': t.status,
            'created_at': t.created_at.isoformat()
        } for t in sent_paginated.items],
        'received': [{
            'id': t.id,
            'amount': float(t.amount),
            'currency': t.currency,
            'reference': t.reference,
            'description': t.description,
            'status': t.status,
            'created_at': t.created_at.isoformat()
        } for t in received_paginated.items],
        'total_sent': sent_paginated.total,
        'total_received': received_paginated.total
    }), 200


@transfer_bp.route('/beneficiaries', methods=['GET'])
@jwt_required
def get_beneficiaries():
    """Liste des bénéficiaires fréquents"""
    # Récupérer les destinataires uniques des transferts
    from sqlalchemy import distinct

    # Cette requête est un peu complexe, version simplifiée
    sent_transactions = Transaction.query.filter_by(
        user_id=request.user_id,
        type='transfer_sent'
    ).all()

    # Extraire les emails des destinataires depuis la description
    beneficiaries = []
    seen = set()

    for t in sent_transactions:
        if t.description and 'to ' in t.description:
            email_part = t.description.split('to ')[-1].split(' -')[0]
            if email_part not in seen and '@' in email_part:
                seen.add(email_part)
                user = User.query.filter_by(email=email_part).first()
                if user:
                    beneficiaries.append({
                        'email': user.email,
                        'name': f"{user.first_name} {user.last_name}",
                        'phone': user.phone,
                        'last_transfer': t.created_at.isoformat()
                    })

    return jsonify({'beneficiaries': beneficiaries[:10]}), 200


@transfer_bp.route('/beneficiary/add', methods=['POST'])
@jwt_required
def add_beneficiary():
    """Ajouter un bénéficiaire (sauvegarder pour transferts rapides)"""
    data = request.json
    email = data.get('email')
    name = data.get('name')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Vérifier que l'utilisateur existe
    recipient = User.query.filter_by(email=email).first()
    if not recipient:
        return jsonify({'error': 'User not found'}), 404

    # Dans un vrai système, stocker dans une table beneficiaries
    # Pour l'instant, on vérifie juste
    return jsonify({
        'message': 'Beneficiary added successfully',
        'beneficiary': {
            'email': recipient.email,
            'name': f"{recipient.first_name} {recipient.last_name}",
            'phone': recipient.phone
        }
    }), 200


@transfer_bp.route('/verify-recipient', methods=['POST'])
@jwt_required
def verify_recipient():
    """Vérifier si un destinataire existe (sans envoyer d'argent)"""
    data = request.json
    email = data.get('email')
    phone = data.get('phone')

    recipient = None
    if email:
        recipient = User.query.filter_by(email=email).first()
    elif phone:
        recipient = User.query.filter_by(phone=phone).first()

    if not recipient:
        return jsonify({'exists': False, 'message': 'Recipient not found'}), 404

    return jsonify({
        'exists': True,
        'recipient': {
            'email': recipient.email,
            'name': f"{recipient.first_name} {recipient.last_name}",
            'phone': recipient.phone,
            'is_verified': recipient.is_verified
        }
    }), 200


@transfer_bp.route('/estimate-fee', methods=['POST'])
@jwt_required
def estimate_fee():
    """Estimer les frais de transfert"""
    data = request.json
    amount = data.get('amount')
    currency = data.get('currency', 'HTG')

    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400

    fee = amount * 0.01  # 1% fee
    net_amount = amount - fee

    return jsonify({
        'amount': amount,
        'currency': currency,
        'fee': fee,
        'fee_percentage': 1.0,
        'net_amount': net_amount,
        'estimated_delivery': 'Instantly'
    }), 200