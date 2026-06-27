# services/notification_service.py
from extensions import db
from models import Notification
from datetime import datetime


def create_notification(user_id, title, message):
    """Créer une notification pour un utilisateur"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def get_user_notifications(user_id, unread_only=False):
    """Récupérer les notifications d'un utilisateur"""
    query = Notification.query.filter_by(user_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    return query.order_by(Notification.created_at.desc()).all()


def mark_as_read(notification_id, user_id):
    """Marquer une notification comme lue"""
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    return False


def send_deposit_confirmation(user_id, amount, method):
    """Envoyer confirmation de dépôt"""
    create_notification(
        user_id,
        "Dépôt confirmé",
        f"Votre dépôt de {amount} HTG via {method} a été confirmé."
    )


def send_card_issued_notification(user_id, card_last4):
    """Envoyer notification d'émission de carte"""
    create_notification(
        user_id,
        "Carte virtuelle émise",
        f"Votre carte virtuelle se terminant par {card_last4} a été créée avec succès."
    )