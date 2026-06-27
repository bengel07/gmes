# routes/admin.py
from flask import Blueprint, request, jsonify
from middleware.auth import jwt_required, admin_required
from extensions import db
from models import User, Wallet, Transaction, Deposit, Withdrawal, KYC, VirtualCard, Payment, AuditLog
from datetime import datetime, timedelta
from sqlalchemy import func

from utils.email_service import send_deposit_confirmation


from utils.email_service import (send_welcome_email, send_deposit_confirmation,
                                  send_withdrawal_confirmation, send_kyc_status_email,
                                  send_transfer_notification, queue_email)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
@admin_required
def admin_dashboard_stats():
    """Admin: Statistiques générales"""

    # Nombre d'utilisateurs
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    verified_users = User.query.filter_by(is_verified=True).count()

    # Volume de transactions
    total_volume = db.session.query(func.sum(Transaction.amount)).filter_by(status='completed').scalar() or 0
    total_fees = db.session.query(func.sum(Transaction.fee)).filter_by(status='completed').scalar() or 0

    # Transactions 30 derniers jours
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_volume = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed',
        Transaction.created_at >= thirty_days_ago
    ).scalar() or 0

    # Cartes actives
    active_cards = VirtualCard.query.filter_by(status='active').count()

    # En attente
    pending_kyc = KYC.query.filter_by(status='pending').count()
    pending_deposits = Deposit.query.filter_by(status='pending').count()
    pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()

    return jsonify({
        'users': {
            'total': total_users,
            'active': active_users,
            'verified': verified_users,
            'pending_kyc': pending_kyc
        },
        'transactions': {
            'total_volume': float(total_volume),
            'total_fees': float(total_fees),
            'recent_volume_30d': float(recent_volume)
        },
        'cards': {
            'active': active_cards
        },
        'pending': {
            'deposits': pending_deposits,
            'withdrawals': pending_withdrawals,
            'kyc': pending_kyc
        }
    }), 200


@admin_bp.route('/users', methods=['GET'])
@jwt_required
@admin_required
def admin_list_users():
    """Admin: Lister tous les utilisateurs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')

    query = User.query

    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.phone.ilike(f'%{search}%')
            )
        )

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)

    return jsonify({
        'users': [{
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'phone': u.phone,
            'is_verified': u.is_verified,
            'is_active': u.is_active,
            'is_admin': u.is_admin,
            'created_at': u.created_at.isoformat(),
            'wallet': {
                'htg': float(u.wallet.balance_htg) if u.wallet else 0,
                'usd': float(u.wallet.balance_usd) if u.wallet else 0
            } if u.wallet else None
        } for u in users.items],
        'total': users.total,
        'page': page,
        'per_page': per_page,
        'pages': users.pages
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required
@admin_required
def admin_get_user(user_id):
    """Admin: Détails d'un utilisateur"""
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'is_verified': user.is_verified,
        'is_active': user.is_active,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat(),
        'wallet': {
            'htg': float(user.wallet.balance_htg) if user.wallet else 0,
            'usd': float(user.wallet.balance_usd) if user.wallet else 0
        } if user.wallet else None
    }), 200


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@jwt_required
@admin_required
def admin_toggle_user_active(user_id):
    """Admin: Activer/Désactiver un utilisateur"""
    if user_id == request.user_id:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_active = not user.is_active
    db.session.commit()

    return jsonify({
        'message': f'User {"activated" if user.is_active else "deactivated"}',
        'user_id': user.id,
        'is_active': user.is_active
    }), 200


@admin_bp.route('/users/<int:user_id>/make-admin', methods=['POST'])
@jwt_required
@admin_required
def admin_make_admin(user_id):
    """Admin: Rendre un utilisateur admin"""
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_admin = True
    db.session.commit()

    return jsonify({
        'message': f'User {user.email} is now admin',
        'user_id': user.id,
        'is_admin': user.is_admin
    }), 200


@admin_bp.route('/transactions', methods=['GET'])
@jwt_required
@admin_required
def admin_list_transactions():
    """Admin: Lister toutes les transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    type_filter = request.args.get('type', '')

    query = Transaction.query

    if type_filter:
        query = query.filter_by(type=type_filter)

    transactions = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=per_page)

    return jsonify({
        'transactions': [{
            'id': t.id,
            'user_id': t.user_id,
            'type': t.type,
            'amount': float(t.amount),
            'fee': float(t.fee) if t.fee else 0,
            'currency': t.currency,
            'status': t.status,
            'reference': t.reference,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        } for t in transactions.items],
        'total': transactions.total,
        'page': page,
        'per_page': per_page
    }), 200


@admin_bp.route('/balance-sheet', methods=['GET'])
@jwt_required
@admin_required
def admin_balance_sheet():
    """Admin: Bilan financier"""

    # Total des wallets
    total_htg = db.session.query(func.sum(Wallet.balance_htg)).scalar() or 0
    total_usd = db.session.query(func.sum(Wallet.balance_usd)).scalar() or 0

    # Volume par type
    deposit_volume = db.session.query(func.sum(Transaction.amount)).filter_by(type='deposit',
                                                                              status='completed').scalar() or 0
    withdrawal_volume = db.session.query(func.sum(Transaction.amount)).filter_by(type='withdrawal',
                                                                                 status='completed').scalar() or 0
    transfer_volume = db.session.query(func.sum(Transaction.amount)).filter_by(type='transfer_sent',
                                                                               status='completed').scalar() or 0
    payment_volume = db.session.query(func.sum(Transaction.amount)).filter_by(type='payment',
                                                                              status='completed').scalar() or 0

    # Frais totaux
    total_fees_collected = db.session.query(func.sum(Transaction.fee)).filter_by(status='completed').scalar() or 0

    return jsonify({
        'wallets_balance': {
            'total_htg': float(total_htg),
            'total_usd': float(total_usd)
        },
        'volume': {
            'deposits': float(deposit_volume),
            'withdrawals': float(withdrawal_volume),
            'transfers': float(transfer_volume),
            'payments': float(payment_volume)
        },
        'fees': {
            'total_collected': float(total_fees_collected)
        }
    }), 200


@admin_bp.route('/audit-logs', methods=['GET'])
@jwt_required
@admin_required
def admin_audit_logs():
    """Admin: Logs d'audit"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    user_id = request.args.get('user_id', type=int)

    query = AuditLog.query

    if user_id:
        query = query.filter_by(user_id=user_id)

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page)

    return jsonify({
        'logs': [{
            'id': l.id,
            'user_id': l.user_id,
            'action': l.action,
            'ip_address': l.ip_address,
            'user_agent': l.user_agent,
            'created_at': l.created_at.isoformat()
        } for l in logs.items],
        'total': logs.total,
        'page': page,
        'per_page': per_page
    }), 200


@admin_bp.route('/system/health', methods=['GET'])
@jwt_required
@admin_required
def admin_system_health():
    """Admin: Santé du système"""
    from datetime import datetime

    # Vérifier base de données
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    # Nombre d'utilisateurs aujourd'hui
    today = datetime.utcnow().date()
    users_today = User.query.filter(func.date(User.created_at) == today).count()

    # Transactions aujourd'hui
    transactions_today = Transaction.query.filter(func.date(Transaction.created_at) == today).count()

    return jsonify({
        'status': 'operational',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'metrics': {
            'users_today': users_today,
            'transactions_today': transactions_today,
            'total_users': User.query.count(),
            'total_transactions': Transaction.query.count()
        }
    }), 200


@admin_bp.route('/deposits/<int:deposit_id>/approve', methods=['POST'])
@jwt_required
@admin_required
def admin_approve_deposit(deposit_id):
    """Admin: Approuver un dépôt"""
    from models import Deposit, Transaction, Wallet
    import uuid

    deposit = Deposit.query.get(deposit_id)

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    if deposit.status != 'pending':
        return jsonify({'error': 'Deposit already processed'}), 400

    deposit.status = 'completed'
    deposit.completed_at = datetime.utcnow()

    user = User.query.get(deposit.user_id)
    wallet = Wallet.query.filter_by(user_id=user.id).first()

    if wallet:
        wallet.balance_htg += deposit.amount

    # Créer transaction
    transaction = Transaction(
        user_id=user.id,
        wallet_id=wallet.id if wallet else None,
        type='deposit',
        amount=deposit.amount,
        fee=0,
        currency='HTG',
        status='completed',
        reference=deposit.reference,
        description=f"Dépôt via {deposit.method}"
    )

    db.session.add(transaction)
    db.session.commit()

    # 📧 ENVOYER EMAIL DE CONFIRMATION
    send_deposit_confirmation(user, deposit)

    return jsonify({
        'message': 'Deposit approved',
        'deposit_id': deposit.id,
        'user_email': user.email
    }), 200


@admin_bp.route('/withdrawals/<int:withdrawal_id>/approve', methods=['POST'])
@jwt_required
@admin_required
def admin_approve_withdrawal(withdrawal_id):
    """Admin: Approuver un retrait"""
    from models import Withdrawal, Transaction, Wallet

    withdrawal = Withdrawal.query.get(withdrawal_id)

    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404

    if withdrawal.status != 'pending':
        return jsonify({'error': 'Withdrawal already processed'}), 400

    user = User.query.get(withdrawal.user_id)
    wallet = Wallet.query.filter_by(user_id=user.id).first()

    # Vérifier solde
    if wallet and wallet.balance_htg < withdrawal.amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    withdrawal.status = 'completed'
    withdrawal.completed_at = datetime.utcnow()

    if wallet:
        wallet.balance_htg -= withdrawal.amount

    # Créer transaction
    transaction = Transaction(
        user_id=user.id,
        wallet_id=wallet.id if wallet else None,
        type='withdrawal',
        amount=withdrawal.amount,
        fee=withdrawal.amount * 0.01,  # 1% fee
        currency='HTG',
        status='completed',
        reference=withdrawal.reference,
        description=f"Retrait via {withdrawal.method}"
    )

    db.session.add(transaction)
    db.session.commit()

    # 📧 ENVOYER EMAIL DE CONFIRMATION
    send_withdrawal_confirmation(user, withdrawal)

    return jsonify({
        'message': 'Withdrawal approved',
        'withdrawal_id': withdrawal.id
    }), 200