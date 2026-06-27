# routes/partner_api.py
from flask import Blueprint, request, jsonify, g
from middleware.rate_limit import rate_limit_required
from services.webhook_service import WebhookService
from extensions import db
from models import Partner, PartnerTransaction
from datetime import datetime, timedelta
import uuid

partner_api_bp = Blueprint('partner_api', __name__, url_prefix='/api/partner/v1')


@partner_api_bp.route('/balance', methods=['GET'])
@rate_limit_required
def get_balance():
    """Vérifier le solde"""
    partner = g.partner

    # Vérifier permission
    if 'BALANCE' not in (partner.permissions or []):
        return jsonify({'error': 'Permission denied'}), 403

    # Calculer le solde disponible
    wallet = partner.wallet if hasattr(partner, 'wallet') else None

    return jsonify({
        'balance': float(wallet.balance_htg) if wallet else 0,
        'currency': 'HTG',
        'partner_id': partner.code,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@partner_api_bp.route('/transfer', methods=['POST'])
@rate_limit_required
def create_transfer():
    """Créer un transfert"""
    partner = g.partner

    # Vérifier permission
    if 'TRANSFER' not in (partner.permissions or []):
        return jsonify({'error': 'Permission denied'}), 403

    data = request.json

    # Validation
    if not data.get('amount') or not data.get('destination'):
        return jsonify({'error': 'amount and destination required'}), 400

    amount = float(data['amount'])

    # Vérifier limite transaction
    if amount > float(partner.per_transaction_limit):
        return jsonify({
            'error': f'Transaction limit exceeded. Max {partner.per_transaction_limit} HTG'
        }), 400

    # Vérifier limites mensuelles/journées
    stats = partner.get_stats()

    if partner.monthly_limit and stats['monthly']['volume'] + amount > float(partner.monthly_limit):
        return jsonify({'error': 'Monthly limit exceeded'}), 429

    if partner.daily_limit and stats['daily']['volume'] + amount > float(partner.daily_limit):
        return jsonify({'error': 'Daily limit exceeded'}), 429

    # Créer la transaction
    reference = f"PTX-{uuid.uuid4().hex[:12].upper()}"

    transaction = PartnerTransaction(
        partner_id=partner.id,
        external_id=data.get('external_id'),
        reference=reference,
        type='TRANSFER',
        amount=amount,
        currency=data.get('currency', 'HTG'),
        fee=amount * 0.01,  # 1% fee
        status='pending',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        metadata=data.get('metadata', {})
    )

    db.session.add(transaction)
    db.session.commit()

    # TODO: Traiter le transfert effectif
    # transaction.status = 'completed'
    # db.session.commit()

    # Mettre à jour les stats du partenaire
    partner.total_transactions += 1
    partner.total_volume += amount
    partner.total_fees += transaction.fee
    db.session.commit()

    # Envoyer webhook
    WebhookService.send_webhook(
        partner.id,
        'transaction.created',
        transaction.to_dict()
    )

    return jsonify({
        'success': True,
        'reference': reference,
        'status': transaction.status,
        'amount': amount,
        'fee': float(transaction.fee),
        'created_at': transaction.created_at.isoformat()
    }), 201


@partner_api_bp.route('/transactions', methods=['GET'])
@rate_limit_required
def get_transactions():
    """Liste des transactions"""
    partner = g.partner

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    transactions = PartnerTransaction.query.filter_by(
        partner_id=partner.id
    ).order_by(
        PartnerTransaction.created_at.desc()
    ).paginate(page=page, per_page=per_page)

    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'page': page,
        'per_page': per_page,
        'pages': transactions.pages
    }), 200


@partner_api_bp.route('/webhook/test', methods=['POST'])
@rate_limit_required
def test_webhook():
    """Tester le webhook"""
    partner = g.partner

    test_payload = {
        'event': 'test.webhook',
        'data': {
            'message': 'This is a test webhook',
            'timestamp': datetime.utcnow().isoformat()
        }
    }

    WebhookService.send_webhook(partner.id, 'test.webhook', test_payload)

    return jsonify({'message': 'Test webhook sent'}), 200