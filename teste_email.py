# from flask import Flask
# from flask_mail import Mail, Message
#
# app = Flask(__name__)
#
# # Configuration Gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'betterdeal3@gmail.com'
# app.config['MAIL_PASSWORD'] = 'pkbt dgaj gvrh sjgq'  # Mot de passe d'application Gmail
# app.config['MAIL_DEFAULT_SENDER'] = ('GMES Pay', 'betterdeal3@gmail.com')
#
# mail = Mail(app)
#
# with app.app_context():
#     try:
#         msg = Message(
#             subject="Test Email GMES",
#             recipients=["TON_EMAIL_DE_TEST@gmail.com"]
#         )
#
#         msg.body = """
# Bonjour,
#
# Ceci est un email de test envoyé depuis GMES.
#
# Si vous recevez ce message, la configuration SMTP fonctionne correctement.
#
# GMES Pay
# """
#
#         mail.send(msg)
#         print("✅ Email envoyé avec succès !")
#
#     except Exception as e:
#         print(f"❌ Erreur : {e}")

import smtplib
import ssl
from email.mime.text import MIMEText

EMAIL = "betterdeal3@gmail.com"
PASSWORD = "pkbtdgajgvrhsjgq"

DESTINATAIRE = "contactbegingeler@gmail.com"

try:
    print("1. Connexion au serveur Gmail...")
    server = smtplib.SMTP("smtp.gmail.com", 587)

    print("2. Activation TLS...")
    server.starttls(context=ssl.create_default_context())

    print("3. Authentification...")
    server.login(EMAIL, PASSWORD)

    print("4. Création du message...")
    msg = MIMEText("Test GMES Email")
    msg["Subject"] = "Test SMTP GMES"
    msg["From"] = EMAIL
    msg["To"] = DESTINATAIRE

    print("5. Envoi...")
    result = server.sendmail(
        EMAIL,
        DESTINATAIRE,
        msg.as_string()
    )

    print("✅ EMAIL ENVOYÉ")
    print("Résultat :", result)

    server.quit()

except Exception as e:
    print("\n❌ ERREUR DÉTECTÉE")
    print(type(e).__name__)
    print(str(e))