from extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20), unique=True)
    # role = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(255))
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    wallet = db.relationship("Wallet", uselist=False, backref="user")
    deposits = db.relationship("Deposit", backref="user")
    withdrawals = db.relationship("Withdrawal", backref="user")
    kyc = db.relationship("KYC", uselist=False, backref="user")
    notifications = db.relationship("Notification", backref="user")
    virtual_cards = db.relationship("VirtualCard", backref="user")
    payments = db.relationship("Payment", backref="user")



    is_agent = db.Column(db.Boolean, default=False)
    agent_code = db.Column(db.String(20), unique=True, nullable=True)
    agent_balance = db.Column(db.Numeric(12, 2), default=0)  # Commission reçue

    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_exp = db.Column(db.DateTime, nullable=True)
    birth_date = db.Column(db.Date, nullable=True)  # À ajouter si besoin

    partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'))
    partner = db.relationship('Partner', backref='users')

    @property
    def age(self):
        if self.birth_date:
            today = datetime.utcnow().date()
            age = today.year - self.birth_date.year
            if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
                age -= 1
            return age
        return None


class EmailNotification(db.Model):
    __tablename__ = "email_notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    type = db.Column(db.String(50))  # welcome, deposit, withdrawal, transfer, kyc, etc.
    recipient_email = db.Column(db.String(120))
    subject = db.Column(db.String(200))
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='email_notifications')


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)


class AgentApplication(db.Model):
    __tablename__ = "agent_applications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    business_name = db.Column(db.String(200))
    business_address = db.Column(db.String(500))
    business_license = db.Column(db.String(100))
    business_type = db.Column(db.String(50))
    initial_capital = db.Column(db.Numeric(12, 2))
    desired_commission = db.Column(db.Numeric(5, 2))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # balance_htg = db.Column(db.Numeric(12, 2), default=0)

    user = db.relationship('User', backref='agent_applications')




class Wallet(db.Model):
    __tablename__ = "wallets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    balance_htg = db.Column(db.Numeric(12, 2), default=0)
    balance_usd = db.Column(db.Numeric(12, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class SanctionedPerson(db.Model):
    __tablename__ = "sanctioned_persons"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    reason = db.Column(db.String(255))
    source = db.Column(db.String(100))  # OFAC, UE, ONU, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id"))
    type = db.Column(db.String(50))
    amount = db.Column(db.Numeric(12, 2))
    fee = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3))
    status = db.Column(db.String(20), default='pending')
    reference = db.Column(db.String(100), unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    user = db.relationship('User', backref='transactions')



    def get_all_transactions(self):
        """Récupère toutes les transactions avec les infos utilisateur"""
        transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
        return [{
            'id': t.reference,
            'user_id': t.user_id,
            'user_name': f"{t.user.first_name} {t.user.last_name}" if t.user else 'N/A',
            'type': t.type,
            'amount': float(t.amount),
            'currency': t.currency,
            'status': t.status,
            'fee': float(t.fee),
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for t in transactions]

    def get_all_users(self):
        users = User.query.all()
        return [{
            'id': u.id,
            'name': f"{u.first_name} {u.last_name}",
            'email': u.email,
            'is_admin': u.is_admin,
            'is_agent': u.is_agent
        } for u in users]


class Deposit(db.Model):
    __tablename__ = "deposits"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Numeric(12, 2))
    method = db.Column(db.String(50))
    reference = db.Column(db.String(100), unique=True)
    receipt_image = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")
    external_ref = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class Withdrawal(db.Model):
    __tablename__ = "withdrawals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Numeric(12, 2))
    method = db.Column(db.String(50))
    destination = db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")
    reference = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class KYC(db.Model):
    __tablename__ = "kyc"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    document_type = db.Column(db.String(50))
    document_number = db.Column(db.String(100))
    document_image = db.Column(db.String(255))
    selfie_image = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")
    rejection_reason = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)


class VirtualCard(db.Model):
    __tablename__ = "virtual_cards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    card_token = db.Column(db.String(255), unique=True)
    card_last4 = db.Column(db.String(4))
    card_brand = db.Column(db.String(20))
    expiry_month = db.Column(db.Integer)
    expiry_year = db.Column(db.Integer)
    status = db.Column(db.String(20), default='active')
    currency = db.Column(db.String(3), default='USD')
    monthly_limit = db.Column(db.Numeric(12, 2), default=5000)
    used_amount = db.Column(db.Numeric(12, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    card_id = db.Column(db.Integer, db.ForeignKey("virtual_cards.id"))
    amount = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3))
    merchant = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    stripe_payment_intent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExchangeRate(db.Model):
    __tablename__ = "exchange_rates"
    id = db.Column(db.Integer, primary_key=True)
    usd_to_htg = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # AJOUTE CES CHAMPS :
    session_id = db.Column(db.String(100))  # Pour suivre la session
    page_url = db.Column(db.String(500))  # Quelle page
    button_id = db.Column(db.String(200))  # Quel bouton
    request_method = db.Column(db.String(10))  # GET, POST, etc
    request_data = db.Column(db.Text)  # Données envoyées
    response_status = db.Column(db.Integer)  # Code HTTP
    duration_ms = db.Column(db.Integer)  # Temps d'exécution
    error_message = db.Column(db.Text)  # Erreurs éventuelles
    browser = db.Column(db.String(100))  # Navigateur
    os = db.Column(db.String(100))  # Système d'exploitation

    user = db.relationship("User", backref="activities")

    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    device_type = db.Column(db.String(50))


# Ajouter dans models.py

class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # L'agent est aussi un user
    agent_code = db.Column(db.String(20), unique=True)
    business_name = db.Column(db.String(200))
    business_address = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    commission_rate = db.Column(db.Numeric(5, 2), default=1.0)  # Commission en %
    balance_htg = db.Column(db.Numeric(12, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    cash_deposits = db.relationship("CashDeposit", backref="agent")


class CashDeposit(db.Model):
    __tablename__ = "cash_deposits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))
    amount = db.Column(db.Numeric(12, 2))
    fee = db.Column(db.Numeric(12, 2), default=0)
    net_amount = db.Column(db.Numeric(12, 2))
    reference = db.Column(db.String(50), unique=True)
    agent_code_used = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    verified_by_agent = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Relations
    user = db.relationship("User", backref="cash_deposits")


# models.py - Ajouter ces modèles pour partenaire

class Partner(db.Model):
    """Partenaire intégré (ex: GMES Microcredit, Banque ABC)"""
    __tablename__ = "partners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)  # GMES001, ABC001
    description = db.Column(db.Text)

    # Configuration
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Contact
    contact_email = db.Column(db.String(200))
    contact_phone = db.Column(db.String(50))
    contact_name = db.Column(db.String(200))

    # Limites
    monthly_limit = db.Column(db.Numeric(12, 2), default=1000000)  # 1M HTG
    per_transaction_limit = db.Column(db.Numeric(12, 2), default=100000)  # 100k HTG
    daily_limit = db.Column(db.Numeric(12, 2), default=500000)  # 500k HTG

    # Wallet partenaire (pour les commissions)
    wallet_balance = db.Column(db.Numeric(12, 2), default=0)

    # Relations
    api_keys = db.relationship("PartnerAPIKey", backref="partner", lazy=True)
    webhooks = db.relationship("PartnerWebhook", backref="partner", lazy=True)
    transactions = db.relationship("PartnerTransaction", backref="partner", lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'contact_name': self.contact_name,
            'monthly_limit': float(self.monthly_limit),
            'per_transaction_limit': float(self.per_transaction_limit),
            'daily_limit': float(self.daily_limit),
            'wallet_balance': float(self.wallet_balance),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PartnerAPIKey(db.Model):
    """Clés API pour les partenaires"""
    __tablename__ = "partner_api_keys"

    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"))

    # Identifiants
    client_id = db.Column(db.String(100), unique=True, nullable=False)
    client_secret = db.Column(db.String(255), nullable=False)  # Hashé
    secret_plain = db.Column(db.String(255))  # Stocké temporairement à la création

    # Permissions (bitmask ou JSON)
    permissions = db.Column(db.JSON, default={
        'can_create_payment': True,
        'can_refund': False,
        'can_check_balance': True,
        'can_webhook': True
    })

    # Configuration
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Rate limiting
    requests_count = db.Column(db.Integer, default=0)
    daily_requests = db.Column(db.Integer, default=0)

    def to_dict(self, include_secret=False):
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'permissions': self.permissions,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }
        if include_secret and self.secret_plain:
            data['client_secret'] = self.secret_plain
        return data


class PartnerWebhook(db.Model):
    """Webhooks pour les partenaires"""
    __tablename__ = "partner_webhooks"

    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"))

    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.String(255))  # Pour signer les payloads
    events = db.Column(db.JSON, default=['payment.created', 'payment.completed'])  # Événements écoutés

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_triggered_at = db.Column(db.DateTime)
    failed_attempts = db.Column(db.Integer, default=0)


class PartnerTransaction(db.Model):
    """Transactions des partenaires"""
    __tablename__ = "partner_transactions"

    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"))

    # Type de transaction
    type = db.Column(db.String(50))  # payment, refund, fee, payout
    status = db.Column(db.String(50), default='pending')  # pending, success, failed

    # Montants
    amount = db.Column(db.Numeric(12, 2))
    fee = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='HTG')

    # Références
    reference = db.Column(db.String(100), unique=True)
    external_reference = db.Column(db.String(100))  # Réf du partenaire

    # Métadonnées
    metadata_json = db.Column(db.JSON, default={})

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'amount': float(self.amount),
            'fee': float(self.fee),
            'currency': self.currency,
            'reference': self.reference,
            'external_reference': self.external_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WebhookLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer)
    url = db.Column(db.String(255))
    payload = db.Column(db.JSON)
    event = db.Column(db.String(100))
    attempts = db.Column(db.Integer, default=0)
    next_retry = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RateLimitLog(db.Model):
    __tablename__ = "rate_limit_logs"

    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"))
    api_key = db.Column(db.String(100))

    endpoint = db.Column(db.String(200))
    method = db.Column(db.String(10))

    ip_address = db.Column(db.String(50))

    was_blocked = db.Column(db.Boolean, default=False)
    reason = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


