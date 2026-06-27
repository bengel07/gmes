# services/webhook_service.py
import requests
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from threading import Thread
from extensions import db
from models import Partner, WebhookLog


class WebhookService:

    @staticmethod
    def send_webhook(partner_id, event_type, payload):
        """Envoie un webhook avec retry automatique"""
        partner = Partner.query.get(partner_id)

        if not partner or not partner.webhook_url:
            return

        log = WebhookLog(
            partner_id=partner.id,
            event_type=event_type,
            payload=payload,
            url=partner.webhook_url,
            max_attempts=partner.webhook_max_retries or 5,
            next_retry_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

        # Envoyer asynchrone
        thread = Thread(target=WebhookService._send_with_retry, args=(log.id,))
        thread.start()

    @staticmethod
    def _send_with_retry(log_id):
        """Fonction interne avec retry"""
        from app import create_app

        app = create_app()
        with app.app_context():
            log = WebhookLog.query.get(log_id)

            if not log or log.is_success:
                return

            partner = Partner.query.get(log.partner_id)

            for attempt in range(log.max_attempts):
                try:
                    # Calculer le délai exponentiel
                    delay = min(300, 30 * (2 ** attempt))  # 30s, 60s, 120s, 240s, 300s max

                    # Attendre avant l'envoi
                    if attempt > 0:
                        time.sleep(delay)

                    # Signer le payload
                    signature = WebhookService._sign_payload(
                        log.payload,
                        partner.webhook_secret or partner.api_secret
                    )

                    # Envoyer la requête
                    response = requests.post(
                        log.url,
                        json={
                            'event': log.event_type,
                            'data': log.payload,
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        headers={
                            'Content-Type': 'application/json',
                            'X-Webhook-Signature': signature,
                            'X-Webhook-Attempt': str(attempt + 1)
                        },
                        timeout=10
                    )

                    # Mettre à jour le log
                    log.attempt = attempt + 1
                    log.status_code = response.status_code
                    log.response_body = response.text[:1000]

                    if 200 <= response.status_code < 300:
                        log.is_success = True
                        log.completed_at = datetime.utcnow()
                        db.session.commit()
                        return
                    else:
                        log.error_message = f"HTTP {response.status_code}"
                        db.session.commit()

                except requests.exceptions.Timeout:
                    log.error_message = "Timeout"
                    db.session.commit()
                except Exception as e:
                    log.error_message = str(e)
                    db.session.commit()

            # Webhook finalement échoué
            log.completed_at = datetime.utcnow()
            db.session.commit()

    @staticmethod
    def _sign_payload(payload, secret):
        """Signe le payload avec HMAC-SHA256"""
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    @staticmethod
    def verify_signature(request, secret):
        """Vérifie la signature entrante d'un webhook"""
        signature = request.headers.get('X-Webhook-Signature')

        if not signature:
            return False

        body = request.get_data(as_text=True)
        expected = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)