from flask import Blueprint, request, jsonify
from middleware.auth import jwt_required
from extensions import db
from models import User, VirtualCard, Wallet, AuditLog, Transaction
from services.card_service import CardService
from services.exchange_service import convert_usd_to_htg
from flask import current_app
import stripe



cards_bp = Blueprint('cards', __name__)
card_service = CardService()


@cards_bp.route('/create', methods=['POST'])
@jwt_required
def create_virtual_card():
    # Vérifier KYC
    user = User.query.get(request.user_id)

    if current_app.config['KYC_REQUIRED_FOR_CARD']:
        from models import KYC
        kyc = KYC.query.filter_by(user_id=request.user_id, status='approved').first()
        if not kyc:
            return jsonify({'error': 'KYC verification required before issuing a card'}), 403

    # Vérifier frais
    wallet = Wallet.query.filter_by(user_id=request.user_id).first()
    fee_usd = current_app.config['VIRTUAL_CARD_ISSUE_FEE']

    if wallet.balance_usd < fee_usd:
        return jsonify({'error': f'Insufficient balance. Need ${fee_usd} USD for card issuance'}), 400

    # Déduire les frais
    wallet.balance_usd -= fee_usd

    # Émettre la carte
    try:
        card_data = card_service.issue_virtual_card(request.user_id, user)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Sauvegarder en base
    virtual_card = VirtualCard(
        user_id=request.user_id,
        card_token=card_data['card_id'],
        card_last4=card_data['last4'],
        card_brand=card_data['brand'],
        expiry_month=card_data['exp_month'],
        expiry_year=card_data['exp_year'],
        currency='USD',
        status='active'
    )
    db.session.add(virtual_card)

    # Transaction
    transaction = Transaction(
        user_id=request.user_id,
        wallet_id=wallet.id,
        type='card_issuance',
        amount=fee_usd,
        fee=0,
        currency='USD',
        status='completed',
        description=f'Virtual card issuance fee - Card ending {card_data["last4"]}'
    )
    db.session.add(transaction)

    # Audit
    audit = AuditLog(
        user_id=request.user_id,
        action='virtual_card_created',
        ip_address=request.remote_addr
    )
    db.session.add(audit)

    db.session.commit()

    return jsonify({
        'message': 'Virtual card created successfully',
        'card': {
            'last4': card_data['last4'],
            'brand': card_data['brand'],
            'expiry': f"{card_data['exp_month']}/{card_data['exp_year']}",
            'cvv': card_data['cvv']
        }
    }), 201


@cards_bp.route('/list', methods=['GET'])
@jwt_required
def list_cards():
    cards = VirtualCard.query.filter_by(user_id=request.user_id).all()

    return jsonify({
        'cards': [{
            'id': c.id,
            'last4': c.card_last4,
            'brand': c.card_brand,
            'expiry': f"{c.expiry_month}/{c.expiry_year}",
            'status': c.status,
            'used_amount': float(c.used_amount),
            'monthly_limit': float(c.monthly_limit),
            'created_at': c.created_at.isoformat()
        } for c in cards]
    }), 200


@cards_bp.route('/<int:card_id>/block', methods=['POST'])
@jwt_required
def block_card(card_id):
    card = VirtualCard.query.filter_by(id=card_id, user_id=request.user_id).first()

    if not card:
        return jsonify({'error': 'Card not found'}), 404

    try:
        result = card_service.block_card(card.card_token)
        card.status = 'blocked'
        db.session.commit()

        return jsonify({'message': 'Card blocked successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500