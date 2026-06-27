# worker/webhook_worker.py
import time
from datetime import datetime
from extensions import db
from models import WebhookLog
from services.webhook_service import WebhookService


def process_pending_webhooks():
    """Traite les webhooks en attente"""
    while True:
        try:
            # Récupérer les webhooks à retenter
            now = datetime.utcnow()
            pending = WebhookLog.query.filter(
                WebhookLog.is_success == False,
                WebhookLog.completed_at == None,
                WebhookLog.next_retry_at <= now
            ).limit(100).all()

            for webhook in pending:
                WebhookService._send_with_retry(webhook.id)

            time.sleep(10)  # Attendre 10 secondes

        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(30)


if __name__ == '__main__':
    print("🚀 Webhook Worker started...")
    process_pending_webhooks()