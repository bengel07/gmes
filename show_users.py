from flask import Flask
from extensions import db
from werkzeug.security import check_password_hash
import os

# Créer l'application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gmespay.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from extensions import db

# Vérifier les colonnes existantes
columns = db.session.execute("PRAGMA table_info(partners)").fetchall()
existing = [col[1] for col in columns]
print("Colonnes existantes:", existing)

# Ajouter les colonnes manquantes
columns_to_add = {
    'monthly_limit': 'NUMERIC(12,2) DEFAULT 1000000',
    'per_transaction_limit': 'NUMERIC(12,2) DEFAULT 100000',
    'daily_limit': 'NUMERIC(12,2) DEFAULT 500000',
    'wallet_balance': 'NUMERIC(12,2) DEFAULT 0'
}

for col, col_type in columns_to_add.items():
    if col not in existing:
        try:
            db.session.execute(f"ALTER TABLE partners ADD COLUMN {col} {col_type}")
            print(f"✅ Colonne {col} ajoutée")
        except Exception as e:
            print(f"❌ Erreur pour {col}: {e}")

db.session.commit()
print("✅ Mise à jour terminée")