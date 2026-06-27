# recreate.py
from extensions import db
from flask import Flask
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gmespay.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Supprimer l'ancienne base
if os.path.exists('gmespay.db'):
    os.remove('gmespay.db')
    print("✅ Ancienne base supprimée")

with app.app_context():
    from models import User, Wallet, Transaction, Deposit, Withdrawal, KYC, VirtualCard, Payment, ExchangeRate, Notification, AuditLog, Agent, CashDeposit
    db.create_all()
    print("✅ Toutes les tables recréées")