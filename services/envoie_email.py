# services/envoie_email.py
from extensions import db, mail
from models import Partner, PartnerAPIKey, PartnerWebhook, PartnerTransaction
from utils.helpers import generate_reference, hash_password
from flask_mail import Message
import secrets
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
from flask import current_app
import uuid


class PartnerEmailService:
    """Service pour l'envoi d'emails aux partenaires"""

    @staticmethod
    def send_welcome_email(partner, client_id, client_secret):
        """Envoie l'email de bienvenue au partenaire"""
        subject = "Bienvenue sur GmesPay - Vos identifiants d'intégration"

        # Template HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0d6efd; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f8f9fa; }}
                .credentials {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .credentials code {{ background: #e9ecef; padding: 2px 8px; border-radius: 3px; }}
                .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #6c757d; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
                .btn {{ display: inline-block; background: #0d6efd; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚀 Bienvenue sur GmesPay</h2>
                </div>

                <div class="content">
                    <p>Bonjour <strong>{partner.contact_name or partner.name}</strong>,</p>

                    <p>Bienvenue sur la plateforme GmesPay ! Voici vos identifiants d'intégration :</p>

                    <div class="credentials">
                        <p><strong>Client ID :</strong><br>
                        <code>{client_id}</code></p>

                        <p><strong>Client Secret :</strong><br>
                        <code>{client_secret}</code></p>

                        <p><strong>Environnement :</strong><br>
                        <span style="background:#198754;color:white;padding:3px 10px;border-radius:3px;">Production</span></p>

                        <p><strong>URL API :</strong><br>
                        <code>https://api.gmespay.com</code></p>

                        <p><strong>Documentation :</strong><br>
                        <a href="https://api.gmespay.com/docs" target="_blank">https://api.gmespay.com/docs</a></p>
                    </div>

                    <div class="warning">
                        <p><strong>⚠️ Important :</strong></p>
                        <p>Conservez votre <strong>Client Secret</strong> en lieu sûr. Il ne sera plus affiché après cette communication.</p>
                    </div>

                    <p><strong>🔔 Webhook :</strong></p>
                    <p>Merci de nous communiquer l'URL de votre webhook afin de recevoir les notifications automatiques.</p>

                    <p style="margin-top: 20px; text-align: center;">
                        <a href="https://api.gmespay.com/docs" class="btn">📖 Voir la documentation</a>
                    </p>

                    <p style="margin-top: 20px;">L'équipe GmesPay</p>
                </div>

                <div class="footer">
                    <p>© 2026 GmesPay - Le pont entre l'argent haïtien et les paiements internationaux</p>
                    <p>
                        <a href="/terms">Conditions d'utilisation</a> | 
                        <a href="/privacy">Confidentialité</a> | 
                        <a href="/contact">Contact</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            msg = Message(
                subject=subject,
                recipients=[partner.contact_email],
                html=html_content,
                sender=("GmesPay", "noreply@gmespay.com")
            )
            mail.send(msg)
            print(f"✅ Email envoyé à {partner.contact_email}")
            return True
        except Exception as e:
            print(f"❌ Erreur envoi email: {e}")
            return False

    @staticmethod
    def send_test_email(email, name="Test"):
        """Envoyer un email de test"""
        subject = "Test GmesPay - Email fonctionne"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0d6efd; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>📧 Test Email GmesPay</h2>
                </div>
                <div class="content">
                    <p>Bonjour <strong>{name}</strong>,</p>
                    <p>Ceci est un email de test pour vérifier que la configuration email fonctionne correctement.</p>
                    <p>Date: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Email de test envoyé à {email}")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False


# Pour une utilisation simple
def send_partner_welcome_email(partner, client_id, client_secret):
    """Fonction wrapper pour faciliter l'appel"""
    return PartnerEmailService.send_welcome_email(partner, client_id, client_secret)