import requests
import hashlib
import hmac
import json
from flask import current_app
from datetime import datetime


class MonCashService:
    def __init__(self):
        self.client_id = current_app.config['MONCASH_CLIENT_ID']
        self.client_secret = current_app.config['MONCASH_CLIENT_SECRET']
        self.base_url = current_app.config['MONCASH_API_URL']
        self.webhook_secret = current_app.config['MONCASH_WEBHOOK_SECRET']

    def get_access_token(self):
        """Obtenir token d'accès MonCash"""
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                timeout = 10
            )
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            current_app.logger.error(f"MonCash token error: {str(e)}")
            raise Exception("Failed to get MonCash token")

    def initiate_payment(self, amount_htg, phone, external_id):
        """Initier un paiement MonCash"""
        try:
            token = self.get_access_token()

            payload = {
                'amount': float(amount_htg),
                'phone': phone,
                'externalId': external_id,
                'description': f'GmesPay deposit - {external_id}',
                'returnUrl': 'https://gmespay.com/deposit/success',
                'webhookUrl': 'https://api.gmespay.com/webhooks/moncash'
            }

            response = requests.post(
                f"{self.base_url}/v1/payments",
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            return {
                'payment_id': result['id'],
                'pay_token': result['payToken'],
                'redirect_url': result['redirectUrl'],
                'status': 'pending'
            }

        except Exception as e:
            current_app.logger.error(f"MonCash payment initiation error: {str(e)}")
            raise Exception(f"Failed to initiate MonCash payment: {str(e)}")

    def verify_payment(self, pay_token):
        """Vérifier le statut d'un paiement"""
        try:
            token = self.get_access_token()

            response = requests.get(
                f"{self.base_url}/v1/payments/{pay_token}",
                headers={'Authorization': f'Bearer {token}'}
            )

            response.raise_for_status()
            result = response.json()

            return {
                'status': result['status'],
                'amount': result.get('amount'),
                'transaction_id': result.get('transactionId')
            }

        except Exception as e:
            current_app.logger.error(f"MonCash verification error: {str(e)}")
            raise Exception("Failed to verify MonCash payment")

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