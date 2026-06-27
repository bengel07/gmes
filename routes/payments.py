# routes/payments.py
from flask import Blueprint, request, jsonify, current_app
from middleware.auth import jwt_required
from extensions import db
from models import User, Wallet, VirtualCard, Payment, Transaction, AuditLog
from services.exchange_service import convert_htg_to_usd
from services.partner_service import PartnerService
from utils.helpers import generate_reference
from datetime import datetime

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/initiate', methods=['POST'])
@jwt_required
def initiate_payment():
    """Initier un paiement international"""
    from services.card_service import CardService


    data = request.json
    card_id = data.get('card_id')
    amount = data.get('amount')
    currency = data.get('currency', 'USD')
    merchant = data.get('merchant')
    description = data.get('description', '')



    # Validations
    if not card_id or not amount or not merchant:
        return jsonify({'error': 'card_id, amount and merchant required'}), 400

    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400

    # Vérifier la carte
    card = VirtualCard.query.filter_by(id=card_id, user_id=request.user_id, status='active').first()
    if not card:
        return jsonify({'error': 'Active card not found'}), 404

    # Vérifier le solde
    wallet = Wallet.query.filter_by(user_id=request.user_id).first()

    if currency == 'USD':
        if not wallet or wallet.balance_usd < amount:
            return jsonify({'error': 'Insufficient USD balance'}), 400
    else:
        amount_usd = convert_htg_to_usd(amount)
        if not wallet or wallet.balance_htg < amount:
            return jsonify({'error': 'Insufficient HTG balance'}), 400

    # Calculer les frais
    fee_percentage = current_app.config.get('INTERNATIONAL_PAYMENT_FEE', 1.0)
    fee = amount * (fee_percentage / 100)
    total_amount = amount + fee

    # Créer le paiement
    reference = generate_reference('PAY')
    payment = Payment(
        user_id=request.user_id,
        card_id=card_id,
        amount=amount,
        currency=currency,
        merchant=merchant,
        description=description,
        status='pending',
        stripe_payment_intent=reference
    )
    db.session.add(payment)

    # Déduire le solde
    if currency == 'USD':
        wallet.balance_usd -= total_amount
    else:
        wallet.balance_htg -= total_amount

    # Transaction
    transaction = Transaction(
        user_id=request.user_id,
        wallet_id=wallet.id,
        type='payment',
        amount=amount,
        fee=fee,
        currency=currency,
        status='completed',
        reference=reference,
        description=f"Payment to {merchant} - {description}"
    )
    db.session.add(transaction)

    # Audit
    audit = AuditLog(
        user_id=request.user_id,
        action='payment_initiated',
        ip_address=request.remote_addr
    )
    db.session.add(audit)

    db.session.commit()

    return jsonify({
        'message': 'Payment initiated successfully',
        'payment_id': payment.id,
        'reference': reference,
        'amount': amount,
        'fee': fee,
        'total': total_amount,
        'currency': currency,
        'merchant': merchant,
        'status': 'completed'
    }), 200


@payments_bp.route('/history', methods=['GET'])
@jwt_required
def payment_history():
    """Historique des paiements"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    payments = Payment.query.filter_by(user_id=request.user_id) \
        .order_by(Payment.created_at.desc()) \
        .paginate(page=page, per_page=per_page)

    return jsonify({
        'payments': [{
            'id': p.id,
            'amount': float(p.amount),
            'currency': p.currency,
            'merchant': p.merchant,
            'description': p.description,
            'status': p.status,
            'reference': p.stripe_payment_intent,
            'card_last4': VirtualCard.query.get(p.card_id).card_last4 if p.card_id else None,
            'created_at': p.created_at.isoformat()
        } for p in payments.items],
        'total': payments.total,
        'page': page,
        'per_page': per_page
    }), 200




bp = Blueprint("payments", __name__)

@bp.route("/api/payments", methods=["POST"])
def create_payment():

    client_id = request.headers.get("X-Client-ID")
    client_secret = request.headers.get("X-Client-Secret")

    partner = PartnerService.verify_api_key(client_id, client_secret)

    if not partner:
        return {"error": "Unauthorized"}, 401

    data = request.json

    payment = {
        "payment_id": "pay_123",
        "payment_url": "http://gmespay/pay/pay_123"
    }

    return payment



