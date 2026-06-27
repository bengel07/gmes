# routes/webhooks.py
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import Deposit, Wallet, Transaction, AuditLog
from services.notification_service import send_deposit_confirmation
from utils.helpers import generate_reference
from services.moncash_service import MonCashService
from datetime import datetime
import json
import hmac
import hashlib

webhooks_bp = Blueprint('webhooks', __name__)


@webhooks_bp.route('/moncash', methods=['POST'])
def moncash_webhook():
    """Webhook pour MonCash"""
    try:
        data = request.json
        signature = request.headers.get('X-MonCash-Signature')

        # Vérifier signature (si configurée)
        webhook_secret = current_app.config.get('MONCASH_WEBHOOK_SECRET')
        if webhook_secret and signature:
            expected = hmac.new(
                webhook_secret.encode(),
                json.dumps(data).encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected, signature):
                current_app.logger.warning("Invalid MonCash webhook signature")
                return jsonify({'error': 'Invalid signature'}), 401

        # Traiter le webhook
        event_type = data.get('event')
        pay_token = data.get('payToken')
        status = data.get('status')
        amount = data.get('amount')
        transaction_id = data.get('transactionId')

        if event_type == 'payment.success' or status == 'success':
            # Trouver le dépôt correspondant
            deposit = Deposit.query.filter_by(external_ref=pay_token, status='pending').first()

            if deposit:
                # Créditer le wallet
                wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
                if wallet:
                    fee = float(deposit.amount) * 0.02  # 2% fee
                    net_amount = float(deposit.amount) - fee

                    wallet.balance_htg += net_amount
                    wallet.updated_at = datetime.utcnow()

                    # Transaction
                    transaction = Transaction(
                        user_id=deposit.user_id,
                        wallet_id=wallet.id,
                        type='deposit',
                        amount=deposit.amount,
                        fee=fee,
                        currency='HTG',
                        status='completed',
                        reference=deposit.reference,
                        description=f'Dépôt via MonCash - Réf: {transaction_id}'
                    )
                    db.session.add(transaction)

                    # Mettre à jour dépôt
                    deposit.status = 'completed'
                    deposit.completed_at = datetime.utcnow()

                    # Audit
                    audit = AuditLog(
                        user_id=deposit.user_id,
                        action='deposit_completed_moncash',
                        ip_address=request.remote_addr
                    )
                    db.session.add(audit)

                    db.session.commit()

                    # Notification
                    send_deposit_confirmation(deposit.user_id, deposit.amount, 'MonCash')

                    current_app.logger.info(f"MonCash deposit completed: {deposit.reference}")

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        current_app.logger.error(f"MonCash webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/natcash', methods=['POST'])
def natcash_webhook():
    """Webhook pour NatCash"""
    try:
        data = request.json
        status = data.get('status')
        reference = data.get('reference')
        amount = data.get('amount')

        if status == 'success':
            deposit = Deposit.query.filter_by(reference=reference, status='pending').first()

            if deposit:
                wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
                if wallet:
                    fee = float(deposit.amount) * 0.02
                    net_amount = float(deposit.amount) - fee

                    wallet.balance_htg += net_amount
                    wallet.updated_at = datetime.utcnow()

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

                    deposit.status = 'completed'
                    deposit.completed_at = datetime.utcnow()

                    db.session.commit()

                    send_deposit_confirmation(deposit.user_id, deposit.amount, 'NatCash')

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        current_app.logger.error(f"NatCash webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook pour Stripe (paiements et cartes)"""
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')

        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

        if webhook_secret and sig_header:
            try:
                import stripe
                stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError as e:
                current_app.logger.error(f"Invalid Stripe payload: {e}")
                return jsonify({'error': 'Invalid payload'}), 400
            except stripe.error.SignatureVerificationError as e:
                current_app.logger.error(f"Invalid Stripe signature: {e}")
                return jsonify({'error': 'Invalid signature'}), 400
        else:
            event = request.json

        event_type = event.get('type')
        event_data = event.get('data', {}).get('object', {})

        # Paiement réussi
        if event_type == 'payment_intent.succeeded':
            payment_intent_id = event_data.get('id')
            # Traiter le paiement réussi
            current_app.logger.info(f"Stripe payment succeeded: {payment_intent_id}")

        # Carte créée
        elif event_type == 'issuing_card.created':
            card_id = event_data.get('id')
            current_app.logger.info(f"Stripe card created: {card_id}")

        # Carte bloquée
        elif event_type == 'issuing_card.shipped':
            card_id = event_data.get('id')
            current_app.logger.info(f"Stripe card shipped: {card_id}")

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        current_app.logger.error(f"Stripe webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/bank-transfer', methods=['POST'])
def bank_transfer_webhook():
    """Webhook pour virement bancaire"""
    try:
        data = request.json
        reference = data.get('reference')
        amount = data.get('amount')
        status = data.get('status')

        if status == 'completed':
            deposit = Deposit.query.filter_by(reference=reference, status='pending_verification').first()

            if deposit:
                wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()
                if wallet:
                    # Virement bancaire = pas de frais
                    net_amount = float(deposit.amount)

                    wallet.balance_htg += net_amount
                    wallet.updated_at = datetime.utcnow()

                    transaction = Transaction(
                        user_id=deposit.user_id,
                        wallet_id=wallet.id,
                        type='deposit',
                        amount=deposit.amount,
                        fee=0,
                        currency='HTG',
                        status='completed',
                        reference=deposit.reference,
                        description='Dépôt par virement bancaire'
                    )
                    db.session.add(transaction)

                    deposit.status = 'completed'
                    deposit.completed_at = datetime.utcnow()

                    db.session.commit()

                    send_deposit_confirmation(deposit.user_id, deposit.amount, 'Virement bancaire')

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        current_app.logger.error(f"Bank transfer webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/test', methods=['POST'])
def test_webhook():
    """Webhook de test pour développement"""
    data = request.json
    current_app.logger.info(f"Test webhook received: {data}")
    return jsonify({'status': 'ok', 'received': data}), 200