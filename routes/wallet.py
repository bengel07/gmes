from flask import Blueprint, request, jsonify,g
from middleware.auth import jwt_required
from extensions import db
from models import User, Wallet, Transaction, AuditLog
from services.exchange_service import convert_htg_to_usd, get_current_usd_to_htg_rate

wallet_bp = Blueprint('wallet', __name__)


@wallet_bp.route('/balance', methods=['GET'])
@jwt_required
def get_balance():
    wallet = Wallet.query.filter_by(user_id=g.user_id).first()

    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404

    return jsonify({
        'htg': float(wallet.balance_htg),
        'usd': float(wallet.balance_usd),
        'currency': 'HTG/USD'
    }), 200


@wallet_bp.route('/transactions', methods=['GET'])
@jwt_required
def get_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    transactions = Transaction.query.filter_by(user_id=g.user_id) \
        .order_by(Transaction.created_at.desc()) \
        .paginate(page=page, per_page=per_page)

    return jsonify({
        'transactions': [{
            'id': t.id,
            'type': t.type,
            'amount': float(t.amount),
            'fee': float(t.fee) if t.fee else 0,
            'currency': t.currency,
            'status': t.status,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        } for t in transactions.items],
        'total': transactions.total,
        'page': page,
        'per_page': per_page,
        'pages': transactions.pages
    }), 200


@wallet_bp.route('/convert', methods=['POST'])
@jwt_required
def convert_currency():
    data = request.json
    amount_htg = data.get('amount_htg')

    if not amount_htg or amount_htg <= 0:
        return jsonify({'error': 'Invalid amount'}), 400

    wallet = Wallet.query.filter_by(user_id=request.user_id).first()

    if not wallet or wallet.balance_htg < amount_htg:
        return jsonify({'error': 'Insufficient HTG balance'}), 400

    usd_amount = convert_htg_to_usd(amount_htg)
    fee = usd_amount * 0.01  # 1% fee

    # Update wallet
    wallet.balance_htg -= amount_htg
    wallet.balance_usd += (usd_amount - fee)
    wallet.updated_at = db.func.now()

    # Create transaction
    transaction = Transaction(
        user_id=request.user_id,
        wallet_id=wallet.id,
        type='currency_conversion',
        amount=amount_htg,
        fee=fee,
        currency='HTG->USD',
        status='completed',
        description=f'Converted {amount_htg} HTG to USD (rate: {get_current_usd_to_htg_rate()})'
    )
    db.session.add(transaction)

    # Audit
    audit = AuditLog(
        user_id=request.user_id,
        action='currency_conversion',
        ip_address=request.remote_addr
    )
    db.session.add(audit)

    db.session.commit()

    return jsonify({
        'converted': float(usd_amount),
        'fee': float(fee),
        'received': float(usd_amount - fee),
        'rate': get_current_usd_to_htg_rate(),
        'new_balance_htg': float(wallet.balance_htg),
        'new_balance_usd': float(wallet.balance_usd)
    }), 200


@wallet_bp.route('/rate', methods=['GET'])
@jwt_required
def get_rate():
    """Obtenir le taux de change actuel"""
    rate = get_current_usd_to_htg_rate()
    return jsonify({
        'usd_to_htg': rate,
        'htg_to_usd': 1 / rate if rate > 0 else 0
    }), 200