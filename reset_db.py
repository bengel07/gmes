from flask import Flask
from extensions import db
from werkzeug.security import generate_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gmespay.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
#
# # from app import app
# from extensions import db
#
# with app.app_context():
#
#     db.session.execute(db.text( "ALTER TABLE users ADD COLUMN partner_id INTEGER)")
#     )
#
#     db.session.commit()
#
#     print("Colonnes ajoutées")




with app.app_context():
    db.session.execute(
        db.text("ALTER TABLE webhook_log ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    )
    db.session.commit()

print("Colonne created_at ajoutée.")
# with app.app_context():
#     from models import User
#
#     # Supprimer l'ancien utilisateur
#     old_user = User.query.filter_by(email="bengel.bg@gmail.com").first()
#     if old_user:
#         db.session.delete(old_user)
#         db.session.commit()
#         print("🗑️ Ancien utilisateur supprimé")

    # # Créer le nouvel admin
    # new_admin = User(
    #     first_name="geler",
    #     last_name="begin",
    #     email="contactbegingeler@gmail.com",  # Email correct
    #     phone="50947035633",  # Ton vrai téléphone
    #     password_hash=generate_password_hash("A-dminB123"),  # Mets TON mot de passe
    #     is_admin=True,
    #     is_active=True,
    #     is_verified=True,
    #     is_agent=False
    # )
    #
    # db.session.add(new_admin)
    # db.session.commit()
    #
    # print("\n✅ Utilisateur créé avec succès!")
    # print("📧 Email: contactbegingeler@gmail.com")
    # print("🔑 Mot de passe: A-dminB123")
    #
    # # Vérifier
    # from werkzeug.security import check_password_hash
    #
    # test = check_password_hash(new_admin.password_hash, "A-dminB123")
    # print(f"✅ Vérification mot de passe: {test}")


# import sqlite3
#
# conn = sqlite3.connect("instance/gmespay.db")  # adapte le chemin
# cursor = conn.cursor()
#
# cursor.execute("PRAGMA table_info(users)")
# for col in cursor.fetchall():
#     print(col)
#
# conn.close()

# import sqlite3
#
# conn = sqlite3.connect("instance/gmespay.db")
# cursor = conn.cursor()
#
# cursor.execute("""
# ALTER TABLE users
# ADD COLUMN birth_date DATE
# """)
#
# conn.commit()
# conn.close()
#
# print("Colonne ajoutée")

# create_email_notifications_table.py
# from flask import Flask
# from extensions import db
# from models import EmailNotification  # Assurez-vous que le modèle existe
#
# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gmespay.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)
#
# with app.app_context():
#     # Crée uniquement les tables qui n'existent pas encore
#     db.create_all()
#     print("✅ Tables manquantes créées (y compris email_notifications).")