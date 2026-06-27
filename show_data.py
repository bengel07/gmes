from app import create_app
from models import (
    User,
    Wallet,
    Transaction,
    Deposit,
    Withdrawal,
    Agent,
    CashDeposit,
    VirtualCard,
    Payment
)

app = create_app('development')

with app.app_context():

    print("\n" + "=" * 60)
    print("UTILISATEURS")
    print("=" * 60)

    users = User.query.all()

    if not users:
        print("Aucun utilisateur trouvé")
    else:
        for u in users:
            print(f"""
ID           : {u.id}
Nom          : {u.first_name} {u.last_name}
Email        : {u.email}
Téléphone    : {u.phone}
Admin        : {u.is_admin}
Agent        : {u.is_agent}
Agent Code   : {u.agent_code}
Vérifié      : {u.is_verified}
Actif        : {u.is_active}
Créé le      : {u.created_at}
            """)

    print("\n" + "=" * 60)
    print("PORTEFEUILLES")
    print("=" * 60)

    wallets = Wallet.query.all()

    for w in wallets:
        print(f"""
Wallet ID    : {w.id}
User ID      : {w.user_id}
Solde HTG    : {w.balance_htg}
Solde USD    : {w.balance_usd}
        """)

    print("\n" + "=" * 60)
    print("AGENTS")
    print("=" * 60)

    agents = Agent.query.all()

    for a in agents:
        print(f"""
Agent ID         : {a.id}
User ID          : {a.user_id}
Code Agent       : {a.agent_code}
Entreprise       : {a.business_name}
Téléphone        : {a.phone}
Commission (%)   : {a.commission_rate}
Solde HTG        : {a.balance_htg}
Actif            : {a.is_active}
        """)

    print("\n" + "=" * 60)
    print("TRANSACTIONS")
    print("=" * 60)

    transactions = Transaction.query.all()

    for t in transactions:
        print(f"""
Transaction ID : {t.id}
User ID        : {t.user_id}
Type           : {t.type}
Montant        : {t.amount}
Devise         : {t.currency}
Statut         : {t.status}
Référence      : {t.reference}
Date           : {t.created_at}
        """)

    print("\n" + "=" * 60)
    print("DEPOTS")
    print("=" * 60)

    deposits = Deposit.query.all()

    for d in deposits:
        print(f"""
Dépôt ID       : {d.id}
User ID        : {d.user_id}
Montant        : {d.amount}
Méthode        : {d.method}
Statut         : {d.status}
Référence      : {d.reference}
        """)

    print("\n" + "=" * 60)
    print("RETRAITS")
    print("=" * 60)

    withdrawals = Withdrawal.query.all()

    for w in withdrawals:
        print(f"""
Retrait ID     : {w.id}
User ID        : {w.user_id}
Montant        : {w.amount}
Destination    : {w.destination}
Statut         : {w.status}
Référence      : {w.reference}
        """)

    print("\n" + "=" * 60)
    print("CARTES VIRTUELLES")
    print("=" * 60)

    cards = VirtualCard.query.all()

    for c in cards:
        print(f"""
Carte ID       : {c.id}
User ID        : {c.user_id}
Derniers 4     : {c.card_last4}
Marque         : {c.card_brand}
Statut         : {c.status}
        """)

    print("\n" + "=" * 60)
    print("PAIEMENTS")
    print("=" * 60)

    payments = Payment.query.all()

    for p in payments:
        print(f"""
Paiement ID    : {p.id}
User ID        : {p.user_id}
Montant        : {p.amount}
Marchand       : {p.merchant}
Statut         : {p.status}
        """)

    print("\n" + "=" * 60)
    print("DEPOTS AGENTS")
    print("=" * 60)

    cash_deposits = CashDeposit.query.all()

    for c in cash_deposits:
        print(f"""
ID             : {c.id}
User ID        : {c.user_id}
Agent ID       : {c.agent_id}
Montant        : {c.amount}
Référence      : {c.reference}
Statut         : {c.status}
        """)

    print("\n" + "=" * 60)
    print("STATISTIQUES")
    print("=" * 60)

    print("Utilisateurs :", User.query.count())
    print("Portefeuilles:", Wallet.query.count())
    print("Agents       :", Agent.query.count())
    print("Transactions :", Transaction.query.count())
    print("Dépôts       :", Deposit.query.count())
    print("Retraits     :", Withdrawal.query.count())
    print("Cartes       :", VirtualCard.query.count())
    print("Paiements    :", Payment.query.count())
    print("CashDeposit  :", CashDeposit.query.count())