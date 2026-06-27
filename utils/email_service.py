from flask_mail import Message
from flask import render_template_string
from extensions import db, mail
from models import EmailNotification, User
from datetime import datetime
import traceback
from flask_mail import Message
from extensions import mail

ADMIN_EMAIL = "betterdeal3@gmail.com"



def send_email(to, subject, template, **kwargs):
    """Envoie un email avec template"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=render_template_string(template, **kwargs)
        )
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, str(e)


def queue_email(user_id, email_type, subject, template, **kwargs):
    """Met en file d'attente un email"""
    user = User.query.get(user_id)
    if not user:
        return False

    notification = EmailNotification(
        user_id=user_id,
        type=email_type,
        recipient_email=user.email,
        subject=subject,
        content=render_template_string(template, **kwargs)
    )
    db.session.add(notification)
    db.session.commit()
    return True


def process_email_queue():
    """Traite la file d'attente des emails (à exécuter en background)"""
    pending = EmailNotification.query.filter_by(status='pending').all()

    for notif in pending:
        try:
            msg = Message(
                subject=notif.subject,
                recipients=[notif.recipient_email],
                html=notif.content
            )
            mail.send(msg)

            notif.status = 'sent'
            notif.sent_at = datetime.utcnow()
        except Exception as e:
            notif.status = 'failed'
            notif.error_message = str(e)

        db.session.commit()


# ============= TEMPLATES EMAIL =============

def send_welcome_email(user):
    """Email de bienvenue"""
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .container { max-width: 600px; margin: auto; padding: 20px; }
            .header { background: #0d6efd; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .footer { background: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; }
            .button { background: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Bienvenue sur GmesPay !</h2>
            </div>
            <div class="content">
                <p>Bonjour {{ user.first_name }} {{ user.last_name }},</p>
                <p>Merci d'avoir créé un compte sur GmesPay, la plateforme de paiement qui connecte Haïti au monde.</p>
                <p>Pour commencer :</p>
                <ul>
                    <li>✅ Vérifiez votre email</li>
                    <li>✅ Complétez votre profil KYC</li>
                    <li>✅ Effectuez votre premier dépôt</li>
                </ul>
                <p>
                    <a href="http://localhost:5000/dashboard"> class="button">
                        Accéder à mon compte
                    </a>
                </p>
            </div>
            <div class="footer">
                <p>© 2026 GmesPay - Le pont entre l'argent haïtien et les paiements internationaux</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(
        user.email,
        "Bienvenue sur GmesPay !",
        template,
        user=user
    )


def send_deposit_confirmation(user, deposit):
    """Confirmation de dépôt"""
    template = """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial, sans-serif; }</style></head>
    <body>
        <h2>💰 Dépôt confirmé</h2>
        <p>Bonjour {{ user.first_name }},</p>
        <p>Votre dépôt de <strong>{{ deposit.amount }} HTG</strong> a été confirmé.</p>
        <p>Référence: {{ deposit.reference }}</p>
        <p>Nouveau solde: <strong>{{ user.wallet.balance_htg }} HTG</strong></p>
        <p>Merci de votre confiance !</p>
    </body>
    </html>
    """
    return send_email(
        user.email,
        "Retrait effectué - GmesPay",
        template,
        user=user,
        deposit=deposit)


def send_withdrawal_confirmation(user, withdrawal):
    """Confirmation de retrait"""
    template = """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial, sans-serif; }</style></head>
    <body>
        <h2>🏧 Retrait effectué</h2>
        <p>Bonjour {{ user.first_name }},</p>
        <p>Votre retrait de <strong>{{ withdrawal.amount }} HTG</strong> a été traité.</p>
        <p>Référence: {{ withdrawal.reference }}</p>
        <p>Méthode: {{ withdrawal.method }}</p>
        <p>Destination: {{ withdrawal.destination }}</p>
    </body>
    </html>
    """
    return send_email(
        user.email,
        "Retrait effectué - GmesPay",
        template,
        user=user,
        withdrawal=withdrawal)

def send_transfer_notification(user, from_user, to_user, amount):
    """Notification de transfert reçu"""
    template = """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial, sans-serif; }</style></head>
    <body>
        <h2>✈️ Transfert reçu</h2>
        <p>Bonjour {{ to_user.first_name }},</p>
        <p>Vous avez reçu <strong>{{ amount }} HTG</strong> de {{ from_user.first_name }} {{ from_user.last_name }}.</p>
        <p>Le montant a été crédité sur votre portefeuille.</p>
    </body>
    </html>
    """
    return send_email(
        user.email,
        from_user=from_user,
        to_user=to_user,
        amount=amount
    )


def send_kyc_status_email(user, status, reason=None):
    """Notification statut KYC"""
    template = """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial, sans-serif; }</style></head>
    <body>
        <h2>✅ Vérification KYC</h2>
        <p>Bonjour {{ user.first_name }},</p>
        {% if status == 'approved' %}
        <p>Félicitations ! Votre compte a été vérifié.</p>
        <p>Vous pouvez maintenant effectuer des transactions jusqu'à <strong>500,000 HTG</strong>.</p>
        {% elif status == 'rejected' %}
        <p>Votre demande de vérification a été refusée.</p>
        <p>Raison: {{ reason }}</p>
        <p>Veuillez soumettre de nouveaux documents.</p>
        {% endif %}
    </body>
    </html>
    """
    return send_email(
        user.email,
        "Statut KYC - GmesPay",
        template,
        user=user)


def send_password_reset_email(user, token):
    """Email réinitialisation mot de passe"""
    reset_link = f"http://127.0.0.1:5000/reset-password?token={token}"
    template = """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial, sans-serif; }</style></head>
    <body>
        <h2>🔐 Réinitialisation mot de passe</h2>
        <p>Bonjour {{ user.first_name }},</p>
        <p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :</p>
        <p><a href="{{ reset_link }}">{{ reset_link }}</a></p>
        <p>Ce lien expire dans 15 minutes.</p>
        <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
    </body>
    </html>
    """
    return send_email(
        user.email,
        "Réinitialisation mot de passe - GmesPay",
        template,
        user=user,
        reset_link=reset_link
    )


def send_agent_request_email(user):
    template = """
    <h2>Demande Agent reçue</h2>

    <p>Bonjour {{ user.first_name }},</p>

    <p>Votre demande pour devenir agent GMES a été reçue.</p>

    <p>Notre équipe analysera votre dossier et vous contactera prochainement.</p>

    <p>Merci.</p>
    """

    return send_email(
        user.email,
        "Bienvenue sur GmesPay !",
        template,
        user=user
    )



def notify_admin_agent_request(user):
    """Notifier l'admin lorsqu'un utilisateur demande à devenir agent"""

    try:
        msg = Message(
            subject="🏪 Nouvelle demande Agent GMES",
            recipients=[ADMIN_EMAIL]
        )

        msg.html = f"""
        <html>
        <body>
            <h2>Nouvelle demande Agent</h2>

            <p>Un utilisateur souhaite devenir agent GMES.</p>

            <hr>

            <p><strong>Nom :</strong> {user.first_name} {user.last_name}</p>
            <p><strong>Email :</strong> {user.email}</p>

            {f'<p><strong>Téléphone :</strong> {user.phone}</p>' if hasattr(user, 'phone') else ''}

            <p><strong>ID Utilisateur :</strong> {user.id}</p>

            <hr>

            <p>Connectez-vous au panneau d'administration pour approuver ou refuser cette demande.</p>

        </body>
        </html>
        """

        mail.send(msg)

        print(f"✅ Notification Agent envoyée à l'admin pour {user.email}")

        return True

    except Exception as e:
        print(f"❌ Erreur notification admin agent : {e}")
        return False



def notify_admin_new_user(user):
    try:
        msg = Message(
            subject="🆕 Nouvel utilisateur GMES",
            recipients=[ADMIN_EMAIL]
        )

        msg.body = f"""
Nouvel utilisateur enregistré

Nom : {user.first_name} {user.last_name}
Email : {user.email}
ID : {user.id}

Un nouvel utilisateur vient de créer un compte sur GMES.
"""

        mail.send(msg)

        print(f"✅ Notification admin envoyée pour {user.email}")
        return True

    except Exception as e:
        print(f"❌ Erreur notification admin : {e}")
        return False


