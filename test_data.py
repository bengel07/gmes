from extensions import db
from models import User, Wallet, Transaction, Deposit, Withdrawal
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import uuid


def create_test_data():
    """Crée des données de test pour tester l'interface"""

    # 1. Créer un admin
    admin = User.query.filter_by(email='admin@test.com').first()
    if not admin:
        admin = User(
            first_name='Admin',
            last_name='Test',
            email='admin@test.com',
            phone='+50912345678',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            is_verified=True,
            is_active=True
        )
        db.session.add(admin)
        db.session.flush()

        wallet = Wallet(user_id=admin.id, balance_htg=0, balance_usd=0)
        db.session.add(wallet)

    # 2. Créer des utilisateurs normaux
    users = []
    for i in range(1, 6):
        user = User.query.filter_by(email=f'user{i}@test.com').first()
        if not user:
            user = User(
                first_name=f'User{i}',
                last_name=f'Test{i}',
                email=f'user{i}@test.com',
                phone=f'+509{i:08d}',
                password_hash=generate_password_hash('password123'),
                is_admin=False,
                is_verified=i % 2 == 0,
                is_active=True
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(
                user_id=user.id,
                balance_htg=random.randint(10000, 500000),
                balance_usd=random.randint(100, 5000)
            )
            db.session.add(wallet)
            users.append(user)

    db.session.commit()

    # 3. Créer des transactions de test
    for user in users:
        for j in range(5):
            tx = Transaction(
                user_id=user.id,
                wallet_id=Wallet.query.filter_by(user_id=user.id).first().id,
                type=random.choice(['deposit', 'transfer', 'payment']),
                amount=random.randint(1000, 50000),
                fee=random.randint(10, 500),
                currency='HTG',
                status=random.choice(['completed', 'pending', 'completed', 'completed']),
                reference=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                description=f"Transaction test {j + 1}",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(tx)

    # 4. Créer des dépôts en attente
    for i in range(3):
        deposit = Deposit(
            user_id=random.choice(users).id,
            amount=random.randint(5000, 100000),
            method='bank_transfer',
            reference=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            status='pending',
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
        )
        db.session.add(deposit)

    # 5. Créer des retraits en attente
    for i in range(2):
        withdrawal = Withdrawal(
            user_id=random.choice(users).id,
            amount=random.randint(10000, 50000),
            method='bank_transfer',
            destination=f"Bank Account {i + 1}",
            reference=f"WDR-{uuid.uuid4().hex[:8].upper()}",
            status='pending',
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        )
        db.session.add(withdrawal)

    db.session.commit()

    print("✅ Données de test créées avec succès !")
    print(f"Admin: admin@test.com / admin123")
    print(f"Utilisateurs: user1@test.com / password123")
    print(f"Total dépôts en attente: {Deposit.query.filter_by(status='pending').count()}")
    print(f"Total retraits en attente: {Withdrawal.query.filter_by(status='pending').count()}")


if __name__ == '__main__':
    from extensions import db
    from flask import Flask
    import os

    # Créer une app Flask temporaire
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gmespay.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        create_test_data()