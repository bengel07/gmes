# services/partner_service.py
from extensions import db
from models import Partner, PartnerAPIKey, PartnerWebhook, PartnerTransaction
from utils.helpers import generate_reference, hash_password
import secrets
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
from flask import current_app

from flask_mail import Message
from extensions import mail
import secrets
import uuid
# Importer la fonction
from services.envoie_email import send_partner_welcome_email
import logging
logger = logging.getLogger(__name__)


class PartnerService:

    @staticmethod
    def create_partner(data):
        """Créer un nouveau partenaire"""
        from flask import url_for

        # Vérifier que le nom est présent
        if not data.get('name'):
            raise ValueError("Le nom du partenaire est requis")

        # Générer un code unique
        code = data.get('code') or f"{data['name'][:4].upper()}{secrets.randbelow(1000):03d}"

        # Générer les clés API
        client_id = f"gmes_{data.get('name', '').lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        client_secret = f"sk_live_{secrets.token_hex(16)}"

        partner = Partner(
            name=data['name'],
            code=code,
            description=data.get('description', ''),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            contact_name=data.get('contact_name'),
            monthly_limit=data.get('monthly_limit', 1000000),
            per_transaction_limit=data.get('per_transaction_limit', 100000),
            daily_limit=data.get('daily_limit', 500000),
            is_active=data.get('is_active', True),
            is_verified = True
        )
        db.session.add(partner)
        db.session.flush()

        # Créer les clés API
        api_key = PartnerAPIKey(
            partner_id=partner.id,
            client_id=client_id,
            client_secret=hash_password(client_secret),
            secret_plain=client_secret,
            permissions=data.get('permissions', {
                'can_create_payment': True,
                'can_refund': False,
                'can_check_balance': True,
                'can_webhook': True
            }),
            expires_at=datetime.utcnow() + timedelta(days=365),
            is_active=True
        )
        db.session.add(api_key)
        db.session.commit()

        # 📧 ENVOYER L'EMAIL DE BIENVENUE
        try:
            email_sent = send_partner_welcome_email(partner, client_id, client_secret)
            if email_sent:
                logger.info(f"✅ Email envoyé à {partner.contact_email}")
            else:
                logger.warning(f"⚠️ Email non envoyé à {partner.contact_email}")
        except Exception as e:
            logger.error(f"❌ Erreur envoi email: {e}")

        return {
            'partner': partner.to_dict(),
            'api_keys': {
                'client_id': client_id,
                'client_secret': client_secret  # Retourné une seule fois
            }
        }

    @staticmethod
    def generate_api_keys(partner_id, permissions=None):
        """Générer des clés API pour un partenaire"""
        client_id = f"gmes_{partner_id}_{secrets.token_hex(8)}"
        client_secret_plain = secrets.token_urlsafe(32)
        client_secret_hashed = hashlib.sha256(client_secret_plain.encode()).hexdigest()

        api_key = PartnerAPIKey(
            partner_id=partner_id,
            client_id=client_id,
            client_secret=client_secret_hashed,
            # secret_plain=client_secret_plain,  # Stocké temporairement
            permissions=permissions or {
                'can_create_payment': True,
                'can_refund': False,
                'can_check_balance': True,
                'can_webhook': True
            },
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        db.session.add(api_key)
        db.session.flush()

        return {
            'client_id': client_id,
            'client_secret': client_secret_plain  # À montrer une seule fois
        }

    @staticmethod
    def verify_api_key(client_id, client_secret):
        """Vérifier les identifiants API"""
        api_key = PartnerAPIKey.query.filter_by(client_id=client_id, is_active=True).first()

        if not api_key:
            return None

        # Vérifier expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Vérifier secret
        secret_hashed = hashlib.sha256(client_secret.encode()).hexdigest()
        if api_key.client_secret != secret_hashed:
            return None

        # Mettre à jour dernière utilisation
        api_key.last_used_at = datetime.utcnow()
        api_key.requests_count += 1
        api_key.daily_requests += 1
        db.session.commit()

        return api_key

    @staticmethod
    def regenerate_secret(api_key_id, partner_id):
        """Régénérer le secret d'une clé API"""
        api_key = PartnerAPIKey.query.filter_by(id=api_key_id, partner_id=partner_id).first()

        if not api_key:
            return None

        new_secret = secrets.token_urlsafe(32)
        api_key.client_secret = hashlib.sha256(new_secret.encode()).hexdigest()
        api_key.secret_plain = new_secret
        db.session.commit()

        return {'client_secret': new_secret}

    @staticmethod
    def create_payment(partner_id, data):
        """Créer un paiement via le partenaire"""
        partner = Partner.query.get(partner_id)

        if not partner or not partner.is_active:
            raise Exception("Partner not active")

        amount = data.get('amount')
        if amount > partner.per_transaction_limit:
            raise Exception(f"Amount exceeds limit of {partner.per_transaction_limit}")

        reference = generate_reference(f"PART_{partner.code}")

        transaction = PartnerTransaction(
            partner_id=partner_id,
            type='payment',
            status='pending',
            amount=amount,
            fee=amount * 0.01,  # 1% fee
            currency=data.get('currency', 'HTG'),
            reference=reference,
            external_reference=data.get('external_reference'),
            metadata_json=data.get('metadata', {})
        )
        db.session.add(transaction)
        db.session.commit()

        # Déclencher webhook
        PartnerService.trigger_webhook(partner_id, 'payment.created', transaction.to_dict())

        return transaction.to_dict()

    @staticmethod
    def add_webhook(partner_id, url, events):
        """Ajouter un webhook pour un partenaire"""
        webhook = PartnerWebhook(
            partner_id=partner_id,
            url=url,
            secret=secrets.token_urlsafe(32),
            events=events
        )
        db.session.add(webhook)
        db.session.commit()

        return {
            'id': webhook.id,
            'url': webhook.url,
            'secret': webhook.secret,
            'events': webhook.events
        }

    @staticmethod
    def trigger_webhook(partner_id, event, payload):
        """Déclencher un webhook pour un partenaire"""
        webhooks = PartnerWebhook.query.filter_by(partner_id=partner_id, is_active=True).all()

        for webhook in webhooks:
            if event in webhook.events:
                try:
                    signature = hmac.new(
                        webhook.secret.encode(),
                        json.dumps(payload).encode(),
                        hashlib.sha256
                    ).hexdigest()

                    response = requests.post(
                        webhook.url,
                        json={
                            'event': event,
                            'timestamp': datetime.utcnow().isoformat(),
                            'data': payload
                        },
                        headers={'X-GmesPay-Signature': signature},
                        timeout=5
                    )

                    webhook.last_triggered_at = datetime.utcnow()
                    if response.status_code >= 400:
                        webhook.failed_attempts += 1

                except Exception as e:
                    webhook.failed_attempts += 1
                    current_app.logger.error(f"Webhook failed: {str(e)}")

        db.session.commit()