# routes/withdrawal.py
from flask import Blueprint, request, jsonify
from middleware.auth import jwt_required
from extensions import db
from models import Withdrawal, Wallet, Transaction, AuditLog
from utils.helpers import generate_reference
from datetime import datetime

withdrawal_bp = Blueprint('withdrawal', __name__)


@withdrawal_bp.route('/initiate', methods=['POST'])
@jwt_required
def initiate_withdrawal():
    """Initier un retrait"""
    data = request.json
    amount = data.get('amount')
    method = data.get('method')  # moncash, bank, cash
    destination = data.get('destination')  # phone number or bank account

    if not amount or not method or not destination:
        return jsonify({'error': 'Amount, method and destination required'}), 400

    wallet = Wallet.query.filter_by(user_id=request.user_id).first()

    if not wallet or wallet.balance_htg < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    reference = generate_reference('WDR')

    withdrawal = Withdrawal(
        user_id=request.user_id,
        amount=amount,
        method=method,
        destination=destination,
        reference=reference,
        status='pending'
    )

    db.session.add(withdrawal)
    db.session.commit()

    from utils.audit import log_action

    log_action(
        action="WITHDRAWAL",
        user_id=user.id,
        request_data={
            "amount": amount,
            "withdrawal_id": withdrawal.id
        }
    )

    return jsonify({
        'withdrawal_id': withdrawal.id,
        'reference': reference,
        'amount': amount,
        'method': method,
        'status': 'pending'
    }), 201


@withdrawal_bp.route('/history', methods=['GET'])
@jwt_required
def withdrawal_history():
    """Historique des retraits"""
    withdrawals = Withdrawal.query.filter_by(user_id=request.user_id) \
        .order_by(Withdrawal.created_at.desc()).all()

    return jsonify({
        'withdrawals': [{
            'id': w.id,
            'amount': float(w.amount),
            'method': w.method,
            'destination': w.destination,
            'reference': w.reference,
            'status': w.status,
            'created_at': w.created_at.isoformat()
        } for w in withdrawals]
    }), 200