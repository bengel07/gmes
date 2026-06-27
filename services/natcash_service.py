# services/natcash_service.py
import requests
import hashlib
import hmac
import json
from flask import current_app
from datetime import datetime


class NatCashService:
    def __init__(self):
        self.client_id = current_app.config.get('NATCASH_CLIENT_ID')
        self.client_secret = current_app.config.get('NATCASH_CLIENT_SECRET')
        self.base_url = current_app.config.get('NATCASH_API_URL')
        self.webhook_secret = current_app.config.get('NATCASH_WEBHOOK_SECRET')

    def get_access_token(self):
        """Obtenir token d'accès NatCash"""
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            current_app.logger.error(f"NatCash token error: {str(e)}")
            raise Exception("Failed to get NatCash token")

    def initiate_payment(self, amount_htg, phone, external_id):
        """Initier un paiement NatCash"""
        try:
            token = self.get_access_token()

            payload = {
                'amount': float(amount_htg),
                'phone': phone,
                'reference': external_id,
                'description': f'GmesPay deposit - {external_id}',
                'callback_url': 'http://127.0.0.1:5000/webhooks/natcash'
            }

            response = requests.post(
                f"{self.base_url}/v1/payments",
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            return {
                'payment_id': result.get('id'),
                'payment_token': result.get('paymentToken'),
                'status': 'pending',
                'message': result.get('message', 'Demande de paiement envoyée')
            }

        except Exception as e:
            current_app.logger.error(f"NatCash payment initiation error: {str(e)}")
            raise Exception(f"Failed to initiate NatCash payment: {str(e)}")

    def verify_payment(self, payment_token):
        """Vérifier le statut d'un paiement"""
        try:
            token = self.get_access_token()

            response = requests.get(
                f"{self.base_url}/v1/payments/{payment_token}",
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            return {
                'status': result.get('status'),
                'amount': result.get('amount'),
                'transaction_id': result.get('transactionId'),
                'phone': result.get('phone')
            }

        except Exception as e:
            current_app.logger.error(f"NatCash verification error: {str(e)}")
            raise Exception("Failed to verify NatCash payment")

    def verify_webhook_signature(self, payload, signature):
        """Vérifier la signature du webhook"""
        try:
            expected = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except:
            return False