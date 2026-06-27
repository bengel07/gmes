# routes/deposit.py
from flask import Blueprint, request, jsonify
from middleware.auth import jwt_required
from extensions import db
from models import Deposit, Wallet, Transaction, AuditLog, Agent, CashDeposit
from services.notification_service import send_deposit_confirmation
from services.natcash_service import NatCashService
from services.moncash_service import MonCashService
from utils.audit import log_action
from utils.helpers import generate_reference
from datetime import datetime

deposit_bp = Blueprint('deposit', __name__)


@deposit_bp.route('/methods', methods=['GET'])
@jwt_required
def get_deposit_methods():
    """Liste des méthodes de dépôt disponibles"""
    methods = [
        {
            'id': 'moncash',
            'name': 'MonCash',
            'icon': 'moncash.png',
            'min_amount': 50,
            'max_amount': 50000,
            'fee_percentage': 2.0,
            'processing_time': 'instantly'
        },
        {
            'id': 'natcash',
            'name': 'NatCash',
            'icon': 'natcash.png',
            'min_amount': 50,
            'max_amount': 50000,
            'fee_percentage': 2.0,
            'processing_time': 'instantly'
        },
        {
            'id': 'bank_transfer',
            'name': 'Virement Bancaire',
            'icon': 'bank.png',
            'min_amount': 500,
            'max_amount': 100000,
            'fee_percentage': 0,
            'processing_time': '1-2 business days'
        },
        {
            'id': 'cash',
            'name': 'Dépôt Cash',
            'icon': 'cash.png',
            'min_amount': 100,
            'max_amount': 25000,
            'fee_percentage': 1.0,
            'processing_time': '24 hours'
        }
    ]
    return jsonify({'methods': methods}), 200


@deposit_bp.route('/initiate', methods=['POST'])
@jwt_required
def initiate_deposit():
    """Initier un dépôt"""
    data = request.json
    method = data.get('method')
    amount = data.get('amount')
    phone = data.get('phone')  # Pour MonCash/NatCash

    if not method or not amount:
        return jsonify({'error': 'Method and amount are required'}), 400

    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than 0'}), 400

    # Vérifier les limites
    if amount > 50000:
        return jsonify({'error': 'Maximum deposit amount is 50,000 HTG'}), 400

    # Créer la référence
    reference = generate_reference('DEP')

    # Créer l'enregistrement de dépôt
    deposit = Deposit(
        user_id=request.user_id,
        amount=amount,
        method=method,
        reference=reference,
        status='pending'
    )

    db.session.add(deposit)

    # Audit log
    audit = AuditLog(
        user_id=request.user_id,
        action=f'deposit_initiated_{method}',
        ip_address=request.remote_addr
    )
    db.session.add(audit)

    db.session.commit()

    # Si c'est MonCash, rediriger vers leur API
    if method == 'moncash':
        return jsonify({
            'deposit_id': deposit.id,
            'reference': reference,
            'amount': amount,
            'method': method,
            'status': 'pending',
            'instruction': f'Envoyez {amount} HTG via MonCash au numéro +509XXXXXXXX',
            'payment_url': f'https://moncash.app/pay/{reference}'  # URL fictive
        }), 201

    return jsonify({
        'deposit_id': deposit.id,
        'reference': reference,
        'amount': amount,
        'method': method,
        'status': 'pending',
        'instruction': f'Veuillez transférer {amount} HTG via {method} avec la référence {reference}'
    }), 201


@deposit_bp.route('/natcash/initiate', methods=['POST'])
@jwt_required
def initiate_natcash_deposit():
    """Initier un dépôt via NatCash"""
    data = request.json
    amount = data.get('amount')
    phone = data.get('phone')

    if not amount or amount < 50:
        return jsonify({'error': 'Minimum deposit is 50 HTG'}), 400

    if not phone:
        return jsonify({'error': 'Phone number required'}), 400

    # Nettoyer le numéro de téléphone
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)

    # Générer une référence unique
    reference = generate_reference('NATCASH')

    # Sauvegarder le dépôt en attente
    deposit = Deposit(
        user_id=request.user_id,
        amount=amount,
        method='natcash',
        reference=reference,
        external_ref=reference,
        status='pending'
    )
    db.session.add(deposit)
    db.session.commit()

    try:
        # Appeler NatCash API
        natcash = NatCashService()
        result = natcash.initiate_payment(amount, phone_clean, reference)

        # Mettre à jour le dépôt
        deposit.external_ref = result['payment_token']
        db.session.commit()

        return jsonify({
            'success': True,
            'deposit_id': deposit.id,
            'reference': reference,
            'payment_token': result['payment_token'],
            'amount': amount,
            'message': 'Demande de paiement NatCash envoyée. Vérifiez votre téléphone.'
        }), 200

    except Exception as e:
        deposit.status = 'failed'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@deposit_bp.route('/natcash/status/<payment_token>', methods=['GET'])
@jwt_required
def check_natcash_status(payment_token):
    """Vérifier le statut d'un paiement NatCash"""
    try:
        natcash = NatCashService()
        result = natcash.verify_payment(payment_token)

        deposit = Deposit.query.filter_by(external_ref=payment_token).first()

        if deposit and result['status'] == 'success':
            deposit.status = 'completed'
            deposit.completed_at = datetime.utcnow()

            # Créditer le wallet
            wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
            if wallet:
                fee = float(deposit.amount) * 0.02
                net_amount = float(deposit.amount) - fee
                wallet.balance_htg += net_amount

                transaction = Transaction(
                    user_id=deposit.user_id,
                    wallet_id=wallet.id,
                    type='deposit',
                    amount=deposit.amount,
                    fee=fee,
                    currency='HTG',
                    status='completed',
                    reference=deposit.reference,
                    description='Dépôt via NatCash'
                )
                db.session.add(transaction)
                db.session.commit()

        return jsonify({
            'status': result['status'],
            'amount': result.get('amount'),
            'deposit_status': deposit.status if deposit else 'not_found'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# routes/deposit.py - Ajouter ces routes pour virement bancaire

@deposit_bp.route('/bank-transfer/info', methods=['GET'])
@jwt_required
def get_bank_transfer_info():
    """Obtenir les informations bancaires pour effectuer un virement"""
    bank_info = {
        'bank_name': current_app.config.get('BANK_NAME', 'Banque de la République d\'Haïti'),
        'account_name': current_app.config.get('BANK_TRANSFER_ACCOUNT_NAME', 'GmesPay SA'),
        'account_number': current_app.config.get('BANK_TRANSFER_ACCOUNT_NUMBER', '12345678901'),
        'bank_code': current_app.config.get('BANK_CODE', 'BRH'),
        'swift_code': 'BRHTHTPP',
        'instructions': [
            'Effectuez un virement bancaire au compte ci-dessus',
            'Utilisez votre référence unique comme motif du virement',
            'Envoyez le reçu du virement via ce formulaire',
            'Le délai de traitement est de 24-48h'
        ],
        'min_amount': 500,
        'max_amount': 100000,
        'fee_percentage': 0
    }
    return jsonify(bank_info), 200


@deposit_bp.route('/bank-transfer/initiate', methods=['POST'])
@jwt_required
def initiate_bank_transfer():
    """Initier un dépôt par virement bancaire"""
    data = request.json
    amount = data.get('amount')

    if not amount or amount < 500:
        return jsonify({'error': 'Minimum deposit is 500 HTG'}), 400

    if amount > 100000:
        return jsonify({'error': 'Maximum deposit is 100,000 HTG'}), 400

    # Générer une référence unique
    reference = generate_reference('BANK')

    # Créer le dépôt
    deposit = Deposit(
        user_id=request.user_id,
        amount=amount,
        method='bank_transfer',
        reference=reference,
        status='pending_verification'
    )
    db.session.add(deposit)
    db.session.commit()

    # Informations bancaires
    bank_info = {
        'reference': reference,
        'amount': amount,
        'bank_name': current_app.config.get('BANK_NAME', 'Banque de la République d\'Haïti'),
        'account_name': current_app.config.get('BANK_TRANSFER_ACCOUNT_NAME', 'GmesPay SA'),
        'account_number': current_app.config.get('BANK_TRANSFER_ACCOUNT_NUMBER', '12345678901'),
        'bank_code': current_app.config.get('BANK_CODE', 'BRH'),
        'instructions': f'Utilisez la référence {reference} comme motif du virement'
    }

    return jsonify({
        'success': True,
        'deposit_id': deposit.id,
        'reference': reference,
        'amount': amount,
        'bank_info': bank_info,
        'message': 'Virement bancaire initié. Envoyez le reçu pour validation.'
    }), 200


@deposit_bp.route('/bank-transfer/upload-receipt', methods=['POST'])
@jwt_required
def upload_bank_receipt():
    """Uploader le reçu du virement bancaire"""
    deposit_id = request.form.get('deposit_id')

    if not deposit_id:
        return jsonify({'error': 'Deposit ID required'}), 400

    deposit = Deposit.query.filter_by(id=deposit_id, user_id=request.user_id).first()

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    if deposit.method != 'bank_transfer':
        return jsonify({'error': 'Not a bank transfer deposit'}), 400

    if 'receipt' not in request.files:
        return jsonify({'error': 'Receipt file required'}), 400

    file = request.files['receipt']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Vérifier l'extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, PDF'}), 400

    # Sauvegarder le fichier
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"bank_receipt_{deposit.user_id}_{timestamp}.{file.filename.rsplit('.', 1)[1].lower()}"

    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'deposits')
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Mettre à jour le dépôt
    deposit.receipt_image = f"/uploads/deposits/{filename}"
    deposit.status = 'pending_verification'
    db.session.commit()

    # Notification à l'admin
    from services.notification_service import create_notification
    create_notification(
        deposit.user_id,
        "Reçu envoyé",
        f"Votre reçu pour le dépôt de {deposit.amount} HTG a été envoyé. En attente de vérification."
    )

    return jsonify({
        'message': 'Receipt uploaded successfully',
        'receipt_url': deposit.receipt_image,
        'status': deposit.status
    }), 200


@deposit_bp.route('/bank-transfer/<int:deposit_id>/confirm', methods=['POST'])
@jwt_required
def confirm_bank_transfer(deposit_id):
    """Admin: Confirmer un virement bancaire"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    deposit = Deposit.query.get(deposit_id)

    if not deposit or deposit.method != 'bank_transfer':
        return jsonify({'error': 'Bank transfer deposit not found'}), 404

    if deposit.status != 'pending_verification':
        return jsonify({'error': f'Deposit already {deposit.status}'}), 400

    # Créditer le wallet
    wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
    if wallet:
        # Pas de frais pour les virements bancaires
        net_amount = float(deposit.amount)

        wallet.balance_htg += net_amount
        wallet.updated_at = datetime.utcnow()

        # Créer transaction
        transaction = Transaction(
            user_id=deposit.user_id,
            wallet_id=wallet.id,
            type='deposit',
            amount=deposit.amount,
            fee=0,
            currency='HTG',
            status='completed',
            reference=deposit.reference,
            description=f'Dépôt par virement bancaire'
        )
        db.session.add(transaction)

    deposit.status = 'completed'
    deposit.completed_at = datetime.utcnow()

    db.session.commit()

    # Notification à l'utilisateur
    from services.notification_service import create_notification
    create_notification(
        deposit.user_id,
        "Dépôt confirmé",
        f"Votre dépôt de {deposit.amount} HTG par virement bancaire a été confirmé."
    )

    return jsonify({
        'message': 'Bank transfer deposit confirmed',
        'deposit_id': deposit.id,
        'amount': float(deposit.amount),
        'user_id': deposit.user_id
    }), 200


@deposit_bp.route('/bank-transfer/<int:deposit_id>/reject', methods=['POST'])
@jwt_required
def reject_bank_transfer(deposit_id):
    """Admin: Rejeter un virement bancaire"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    data = request.json
    reason = data.get('reason', 'Reçu invalide ou non conforme')

    deposit = Deposit.query.get(deposit_id)

    if not deposit or deposit.method != 'bank_transfer':
        return jsonify({'error': 'Bank transfer deposit not found'}), 404

    deposit.status = 'rejected'
    deposit.completed_at = datetime.utcnow()
    db.session.commit()

    # Notification à l'utilisateur
    from services.notification_service import create_notification
    create_notification(
        deposit.user_id,
        "Dépôt rejeté",
        f"Votre dépôt de {deposit.amount} HTG a été rejeté. Raison: {reason}"
    )

    return jsonify({
        'message': 'Bank transfer deposit rejected',
        'deposit_id': deposit.id,
        'reason': reason
    }), 200



@deposit_bp.route('/moncash/initiate', methods=['POST'])
@jwt_required
def initiate_moncash_deposit():
    """Initier un dépôt via MonCash"""
    data = request.json
    amount = data.get('amount')
    phone = data.get('phone')

    if not amount or amount < 50:
        return jsonify({'error': 'Minimum deposit is 50 HTG'}), 400

    if not phone:
        return jsonify({'error': 'Phone number required'}), 400

    # Nettoyer le numéro de téléphone
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)

    # Générer une référence unique
    reference = generate_reference('MONCASH')

    # Sauvegarder le dépôt en attente
    deposit = Deposit(
        user_id=request.user_id,
        amount=amount,
        method='moncash',
        reference=reference,
        external_ref=reference,
        status='pending'
    )
    db.session.add(deposit)
    db.session.commit()

    try:
        # Appeler MonCash API
        moncash = MonCashService()
        result = moncash.initiate_payment(amount, phone_clean, reference)

        # Mettre à jour le dépôt avec le pay_token
        deposit.external_ref = result['pay_token']
        db.session.commit()

        return jsonify({
            'success': True,
            'deposit_id': deposit.id,
            'reference': reference,
            'pay_token': result['pay_token'],
            'redirect_url': result['redirect_url'],
            'amount': amount,
            'message': 'Redirigez-vous vers MonCash pour finaliser le paiement'
        }), 200

    except Exception as e:
        deposit.status = 'failed'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@deposit_bp.route('/moncash/status/<pay_token>', methods=['GET'])
@jwt_required
def check_moncash_status(pay_token):
    """Vérifier le statut d'un paiement MonCash"""
    try:
        moncash = MonCashService()
        result = moncash.verify_payment(pay_token)

        deposit = Deposit.query.filter_by(external_ref=pay_token).first()

        if deposit and result['status'] == 'success':
            deposit.status = 'completed'
            deposit.completed_at = datetime.utcnow()

            # Créditer le wallet
            wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
            if wallet:
                fee = float(deposit.amount) * 0.02
                net_amount = float(deposit.amount) - fee
                wallet.balance_htg += net_amount

                transaction = Transaction(
                    user_id=deposit.user_id,
                    wallet_id=wallet.id,
                    type='deposit',
                    amount=deposit.amount,
                    fee=fee,
                    currency='HTG',
                    status='completed',
                    reference=deposit.reference,
                    description=f'Dépôt via MonCash'
                )
                db.session.add(transaction)
                db.session.commit()

        return jsonify({
            'status': result['status'],
            'amount': result.get('amount'),
            'deposit_status': deposit.status if deposit else 'not_found'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# routes/deposit.py - Ajouter ces routes

@deposit_bp.route('/cash/agents', methods=['GET'])
@jwt_required
def get_cash_agents():
    """Liste des agents cash disponibles"""
    from services.cash_service import CashService

    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lng', type=float)

    agents = CashService.get_nearby_agents(latitude, longitude)

    return jsonify({
        'agents': agents,
        'message': 'Présentez-vous chez un agent avec la référence générée'
    }), 200


@deposit_bp.route('/cash/initiate', methods=['POST'])
@jwt_required
def initiate_cash_deposit():
    """Initier un dépôt cash"""
    from services.cash_service import CashService

    data = request.json
    amount = data.get('amount')
    agent_code = data.get('agent_code')

    if not amount or not agent_code:
        return jsonify({'error': 'Amount and agent_code required'}), 400

    try:
        result = CashService.initiate_cash_deposit(request.user_id, amount, agent_code)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@deposit_bp.route('/cash/confirm', methods=['POST'])
@jwt_required
def confirm_cash_deposit():
    """Agent confirme un dépôt cash (route spéciale agent)"""
    from services.cash_service import CashService
    from middleware.auth import agent_required

    # Vérifier que l'utilisateur est un agent
    # (À implémenter: decorator @agent_required)

    data = request.json
    reference = data.get('reference')

    if not reference:
        return jsonify({'error': 'Reference required'}), 400

    # Récupérer l'agent_id depuis le token
    agent = Agent.query.filter_by(user_id=request.user_id).first()
    if not agent:
        return jsonify({'error': 'Agent account required'}), 403

    try:
        result = CashService.confirm_cash_deposit(agent.id, reference)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@deposit_bp.route('/cash/status/<reference>', methods=['GET'])
@jwt_required
def get_cash_deposit_status(reference):
    """Vérifier le statut d'un dépôt cash"""
    cash_deposit = CashDeposit.query.filter_by(reference=reference).first()

    if not cash_deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    if cash_deposit.user_id != request.user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'reference': cash_deposit.reference,
        'amount': float(cash_deposit.amount),
        'fee': float(cash_deposit.fee),
        'net_amount': float(cash_deposit.net_amount),
        'status': cash_deposit.status,
        'agent': {
            'name': cash_deposit.agent.business_name if cash_deposit.agent else None,
            'address': cash_deposit.agent.business_address if cash_deposit.agent else None
        } if cash_deposit.agent else None,
        'created_at': cash_deposit.created_at.isoformat(),
        'completed_at': cash_deposit.completed_at.isoformat() if cash_deposit.completed_at else None
    }), 200

@deposit_bp.route('/confirm', methods=['POST'])
@jwt_required
def confirm_deposit():
    """Confirmer un dépôt (pour les méthodes manuelles)"""
    data = request.json
    deposit_id = data.get('deposit_id')
    receipt_image = data.get('receipt_image')  # URL de l'image du reçu

    if not deposit_id:
        return jsonify({'error': 'Deposit ID required'}), 400

    deposit = Deposit.query.filter_by(id=deposit_id, user_id=request.user_id).first()

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    if deposit.status != 'pending':
        return jsonify({'error': f'Deposit already {deposit.status}'}), 400

    if receipt_image:
        deposit.receipt_image = receipt_image

    deposit.status = 'pending_verification'
    db.session.commit()

    log_action(
        action="DEPOSIT",
        user_id=user.id,
        request_data={
            "amount": amount,
            "method": method
        }
    )

    return jsonify({
        'message': 'Deposit confirmation submitted for verification',
        'deposit_id': deposit.id,
        'status': 'pending_verification'
    }), 200


@deposit_bp.route('/history', methods=['GET'])
@jwt_required
def deposit_history():
    """Historique des dépôts"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    deposits = Deposit.query.filter_by(user_id=request.user_id) \
        .order_by(Deposit.created_at.desc()) \
        .paginate(page=page, per_page=per_page)

    return jsonify({
        'deposits': [{
            'id': d.id,
            'amount': float(d.amount),
            'method': d.method,
            'reference': d.reference,
            'status': d.status,
            'receipt_image': d.receipt_image,
            'created_at': d.created_at.isoformat(),
            'completed_at': d.completed_at.isoformat() if d.completed_at else None
        } for d in deposits.items],
        'total': deposits.total,
        'page': page,
        'per_page': per_page
    }), 200


@deposit_bp.route('/<int:deposit_id>/status', methods=['GET'])
@jwt_required
def get_deposit_status(deposit_id):
    """Vérifier le statut d'un dépôt"""
    deposit = Deposit.query.filter_by(id=deposit_id, user_id=request.user_id).first()

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    return jsonify({
        'id': deposit.id,
        'status': deposit.status,
        'amount': float(deposit.amount),
        'reference': deposit.reference,
        'created_at': deposit.created_at.isoformat()
    }), 200


# Routes pour l'admin
@deposit_bp.route('/admin/pending', methods=['GET'])
@jwt_required
def admin_pending_deposits():
    """Admin: Voir les dépôts en attente"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()  # Vérifier admin

    deposits = Deposit.query.filter_by(status='pending_verification') \
        .order_by(Deposit.created_at.asc()).all()

    return jsonify({
        'pending_deposits': [{
            'id': d.id,
            'user_id': d.user_id,
            'amount': float(d.amount),
            'method': d.method,
            'reference': d.reference,
            'receipt_image': d.receipt_image,
            'created_at': d.created_at.isoformat()
        } for d in deposits]
    }), 200


@deposit_bp.route('/admin/<int:deposit_id>/approve', methods=['POST'])
@jwt_required
def admin_approve_deposit(deposit_id):
    """Admin: Approuver un dépôt"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    deposit = Deposit.query.get(deposit_id)

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    if deposit.status not in ['pending', 'pending_verification']:
        return jsonify({'error': f'Cannot approve deposit with status {deposit.status}'}), 400

    # Mettre à jour le wallet
    wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
    if wallet:
        # Appliquer les frais
        fee = float(deposit.amount) * 0.02  # 2% fee
        net_amount = float(deposit.amount) - fee

        wallet.balance_htg += net_amount
        wallet.updated_at = datetime.utcnow()

        # Créer transaction
        transaction = Transaction(
            user_id=deposit.user_id,
            wallet_id=wallet.id,
            type='deposit',
            amount=deposit.amount,
            fee=fee,
            currency='HTG',
            status='completed',
            description=f'Dépôt via {deposit.method} - Réf: {deposit.reference}'
        )
        db.session.add(transaction)

    deposit.status = 'completed'
    deposit.completed_at = datetime.utcnow()

    # Notification
    send_deposit_confirmation(deposit.user_id, deposit.amount, deposit.method)

    db.session.commit()

    return jsonify({
        'message': 'Deposit approved successfully',
        'deposit_id': deposit.id,
        'amount': float(deposit.amount),
        'net_amount': float(net_amount) if 'net_amount' in locals() else float(deposit.amount),
        'fee': float(fee) if 'fee' in locals() else 0
    }), 200


@deposit_bp.route('/admin/<int:deposit_id>/reject', methods=['POST'])
@jwt_required
def admin_reject_deposit(deposit_id):
    """Admin: Rejeter un dépôt"""
    from middleware.auth import admin_required
    admin_required(lambda: None)()

    deposit = Deposit.query.get(deposit_id)

    if not deposit:
        return jsonify({'error': 'Deposit not found'}), 404

    deposit.status = 'rejected'
    deposit.completed_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': 'Deposit rejected',
        'deposit_id': deposit.id
    }), 200