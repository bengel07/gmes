import os
import uuid
from datetime import datetime, timedelta
import logging
from config import config
from extensions import db, migrate, cors
from config import Config

from werkzeug.security import generate_password_hash

from utils.audit import log_action
from utils.helpers import hash_password  # Au début du fichier

import jwt
from flask import current_app


from models import User, Agent, Transaction, AgentApplication, SanctionedPerson, Partner, PartnerAPIKey, WebhookLog
from functools import wraps

from flask import (render_template, session, redirect,
                   url_for, flash, jsonify,g, Flask, request,)

from utils.email_service import (send_welcome_email, send_agent_request_email,
                                 notify_admin_agent_request,  notify_admin_new_user)

import time

from flask_mail import Mail, Message



def create_admin_if_not_exists():
    from models import User
    from utils.helpers import hash_password  # ← Import correct

    admin_email = "contactbegingeler@gmail.com"
    admin = User.query.filter_by(email=admin_email).first()

    if not admin:
        print("🔧 Création automatique de l'admin...")

        admin = User(
            first_name="Geler",
            last_name="Begin",
            email=admin_email,
            phone="50947035633",
            password_hash=hash_password("A-dminB123"),  # ← Utilise hash_password
            is_admin=True,
            is_active=True,
            is_verified=True,
            is_agent=False
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé avec succès!")
        print("📧 Email: contactbegingeler@gmail.com")
        print("🔑 Mot de passe: A-dminB123")
    else:
        print("✅ Admin déjà existant")


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialiser extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Middleware
    from middleware.auth import jwt_required
    app.jwt_required = jwt_required

    from middleware.rate_limit import rate_limit_required

    # Importer modèles
    from models import User, Wallet, Transaction, Deposit, Withdrawal, KYC, Notification, ExchangeRate, AuditLog, \
        VirtualCard, Payment

    # Enregistrer blueprints
    from routes.auth import auth_bp
    from routes.wallet import wallet_bp
    from routes.deposit import deposit_bp
    from routes.withdrawal import withdrawal_bp
    from routes.transfer import transfer_bp
    from routes.cards import cards_bp
    from routes.payments import payments_bp
    from routes.kyc import kyc_bp
    from routes.admin import admin_bp
    from routes.webhooks import webhooks_bp

    # Dans app.py, ajouter
    from routes.partner_routes import partner_bp

    from routes.partner_api import partner_api_bp


    # Enregistrer le blueprint
    app.register_blueprint(partner_api_bp)

    app.register_blueprint(partner_bp, url_prefix='/api/partner')

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(wallet_bp, url_prefix='/api/wallet')
    app.register_blueprint(deposit_bp, url_prefix='/api/deposit')
    app.register_blueprint(withdrawal_bp, url_prefix='/api/withdrawal')
    app.register_blueprint(transfer_bp, url_prefix='/api/transfer')
    app.register_blueprint(cards_bp, url_prefix='/api/cards')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(kyc_bp, url_prefix='/api/kyc')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(webhooks_bp, url_prefix='/webhooks')



    # Configuration email
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # ou smtp.office365.com, etc.
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'betterdeal3@gmail.com'  # Ton email
    app.config['MAIL_PASSWORD'] = 'pkbt dgaj gvrh sjgq'  # Mot de passe application
    app.config['MAIL_DEFAULT_SENDER'] = ('GmesPay', 'betterdeal3@gmail.com')

    # app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config.from_object(Config)

    mail = Mail(app)




    def role_required(role):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):

                user = User.query.get(g.user_id)

                if not user:
                    return jsonify({"error": "User not found"}), 404

                if role == "admin" and not user.is_admin:
                    return jsonify({"error": "Admin only"}), 403

                if role == "agent" and not user.is_agent:
                    return jsonify({"error": "Agent only"}), 403

                if role == "client" and (user.is_agent or user.is_admin):
                    return jsonify({"error": "Client only"}), 403

                g.current_user = user

                return f(*args, **kwargs)

            return wrapper

        return decorator

    def login_requis(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Veuillez vous connecter', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    def log_activity(action_name):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                start_time = time.time()

                # Utiliser request (c'est CORRECT ici)
                session_id = session.get('session_id', request.remote_addr)
                user_agent = request.user_agent.string if hasattr(request, 'user_agent') else ''

                try:
                    response = f(*args, **kwargs)
                    status = 200
                    error = None
                except Exception as e:
                    status = 500
                    error = str(e)
                    raise
                finally:
                    duration = int((time.time() - start_time) * 1000)

                    log = AuditLog(
                        user_id=session.get('user_id'),
                        session_id=session_id,
                        action=action_name,
                        ip_address=request.remote_addr,
                        user_agent=user_agent,
                        page_url=request.url,
                        request_method=request.method,
                        response_status=status,
                        duration_ms=duration,
                        error_message=error,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(log)
                    db.session.commit()

                return response

            return decorated_function

        return decorator



    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if not session.get('user_id'):
                return redirect(url_for('login'))

            if not session.get('is_admin'):
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)

        return decorated

    def redirect_by_role(token):
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )

            user = payload.get("user")

            # sécurise fallback
            if not user:
                return redirect(url_for("login"))

            if user.get("is_admin"):
                return redirect("/admin/dashboard")

            elif user.get("is_agent"):
                return redirect("/agent/agent_dashboard")

            else:
                return redirect("/dashboard")

        except Exception:
            return redirect(url_for("login"))

    def validate_token(token):
        """Valide le token JWT et retourne l'utilisateur"""
        try:
            # Décoder le token
            payload = jwt.decode(
                token,
                app.config.get('SECRET_KEY', 'votre_secret_key_ici'),
                algorithms=['HS256']
            )

            # Vérifier si le token n'a pas expiré
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                return None

            # Récupérer l'utilisateur
            user_id = payload.get('user_id')
            if not user_id:
                return None

            user = User.query.get(user_id)
            return user

        except jwt.ExpiredSignatureError:
            print("Token expiré")
            return None
        except jwt.InvalidTokenError:
            print("Token invalide")
            return None
        except Exception as e:
            print(f"Erreur validation token: {e}")
            return None




    # Route santé
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200

    # Gestionnaire erreurs global
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Internal error: {error}')
        return jsonify({'error': 'Internal server error'}), 500

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/register')
    def register():
        return render_template('register.html')

    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        return render_template('admin/dashboard.html')

    @app.route('/dashboard')
    def dashboard():

        print(f"=== DASHBOARD ===")
        print(f"Session user_id: {session.get('user_id')}")
        print(f"Session is_admin: {session.get('is_admin')}")

        token = request.cookies.get('token')
        print(f"Cookie token: {token[:20] if token else 'None'}")

        auth_header = request.headers.get('Authorization', '')
        print(f"Auth header: {auth_header[:20] if auth_header else 'None'}")

        # Essayer de restaurer la session depuis le token
        if not session.get('user_id'):
            # Vérifier si token existe dans la requête
            token = request.cookies.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')

            if token:
                # Valider le token et restaurer la session
                user = validate_token(token)
                if user:
                    session['user_id'] = user.id
                    session['is_admin'] = user.is_admin
                    session['is_agent'] = user.is_agent

        # Si toujours pas de session, rediriger
        if not session.get('user_id'):
            return redirect(url_for('login'))

        return render_template('dashboard.html')


    @app.route('/wallet')
    def wallet():
        if not session.get('user_id'):
            flash('Veuillez vous connecter pour accéder au tableau de bord', 'warning')
            return redirect(url_for('login'))
        return render_template('wallet.html')

    @app.route('/cards')
    def cards():
        if not session.get('user_id'):
            flash('Veuillez vous connecter pour accéder au tableau de bord', 'warning')
            return redirect(url_for('login'))
        return render_template('cards.html')

    @app.route('/transfer')
    def transfer():
        if not session.get('user_id'):
            flash('Veuillez vous connecter pour accéder au tableau de bord', 'warning')
            return redirect(url_for('login'))
        return render_template('transfer.html')

    @app.route('/profile')
    def profile():
        if not session.get('user_id'):
            flash('Veuillez vous connecter pour accéder au tableau de bord', 'warning')
            return redirect(url_for('login'))
        return render_template('profile.html')



    # Ajouter dans app.py
    @app.route('/agent/login')
    def agent_login_page():
        return render_template('agent/login.html')

    @app.before_request
    def track_page_visit():

        ignored = [
            "/static/",
            "/favicon.ico"
        ]

        if any(request.path.startswith(x) for x in ignored):
            return

        if session.get("user_id"):
            log_action(
                action="PAGE_VISIT",
                user_id=session.get("user_id")
            )

    @app.errorhandler(Exception)
    def handle_error(e):

        log_action(
            action="ERROR",
            user_id=session.get("user_id"),
            error_message=str(e),
            response_status=500
        )

        raise e



    @app.route('/agent/agent_dashboard')
    def agent_dashboard():
        if not session.get('user_id'):
            flash('Veuillez vous connecter pour accéder au tableau de bord', 'warning')
            return redirect(url_for('login'))
            # Vérifier que l'utilisateur est bien un agent
        if not session.get('is_agent'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('agent/agent_dashboard.html')



    @app.route('/reset-password')
    def reset_password_page():
        return render_template('reset_password.html')

    @app.route('/admin/deposits/approve')
    @login_requis
    def admin_deposits_approve():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import Deposit, User

        # Récupérer tous les dépôts en attente
        pending_deposits = Deposit.query.filter_by(status='pending').order_by(Deposit.created_at.desc()).all()

        # Récupérer tous les dépôts
        all_deposits = Deposit.query.order_by(Deposit.created_at.desc()).all()

        return render_template('admin_deposits.html',
                               pending_deposits=pending_deposits,
                               all_deposits=all_deposits)

    @app.route('/api/admin/deposits/<int:id>/approve', methods=['POST'])
    @login_requis
    def api_approve_deposit(id):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403

        from models import Deposit, Transaction, Wallet
        from extensions import db
        import uuid

        deposit = Deposit.query.get(id)

        if not deposit:
            return jsonify({'success': False, 'message': 'Dépôt non trouvé'})

        if deposit.status != 'pending':
            return jsonify({'success': False, 'message': 'Dépôt déjà traité'})

        # Mettre à jour le statut
        deposit.status = 'completed'
        deposit.completed_at = datetime.utcnow()

        # Créer la transaction
        wallet = Wallet.query.filter_by(user_id=deposit.user_id).first()

        if not wallet:
            return jsonify({'success': False, 'message': 'Portefeuille non trouvé'})

        # Ajouter au portefeuille
        wallet.balance_htg += deposit.amount

        # Créer la transaction
        transaction = Transaction(
            user_id=deposit.user_id,
            wallet_id=wallet.id,
            type='deposit',
            amount=deposit.amount,
            fee=0,
            currency='HTG',
            status='completed',
            reference=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            description=f"Dépôt via {deposit.method}"
        )

        db.session.add(transaction)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Dépôt approuvé'})

    @app.route('/api/admin/deposits/<int:id>/reject', methods=['POST'])
    @login_requis
    def api_reject_deposit(id):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403

        from models import Deposit
        from extensions import db

        deposit = Deposit.query.get(id)

        if not deposit:
            return jsonify({'success': False, 'message': 'Dépôt non trouvé'})

        if deposit.status != 'pending':
            return jsonify({'success': False, 'message': 'Dépôt déjà traité'})

        deposit.status = 'rejected'
        db.session.commit()

        return jsonify({'success': True, 'message': 'Dépôt rejeté'})

    @app.route('/admin/kyc')
    @login_requis
    def admin_kyc():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import KYC, User

        # Récupérer tous les KYC en attente
        pending_kyc = KYC.query.filter_by(status='pending').all()

        # Récupérer tous les KYC
        all_kyc = KYC.query.all()

        return render_template('admin/admin_kyc.html',
                               pending_kyc=pending_kyc,
                               all_kyc=all_kyc)

    @app.route('/admin/withdrawals/approve')
    @login_requis
    def admin_withdrawals_approve():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import Withdrawal, User

        # Récupérer tous les retraits en attente
        pending_withdrawals = Withdrawal.query.filter_by(status='pending').order_by(Withdrawal.created_at.desc()).all()

        # Récupérer tous les retraits
        all_withdrawals = Withdrawal.query.order_by(Withdrawal.created_at.desc()).all()

        return render_template('admin/admin_withdrawals.html',
                               pending_withdrawals=pending_withdrawals,
                               all_withdrawals=all_withdrawals)

    @app.route('/admin/transfer/new')
    @login_requis
    def admin_transfer_new():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import User

        # Récupérer tous les utilisateurs pour le sélecteur
        users = User.query.all()

        return render_template('admin/admin_transfer.html', users=users)

    @app.route('/api/admin/transfer', methods=['POST'])
    @login_requis
    def api_admin_transfer():
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403

        from models import User, Wallet, Transaction
        from extensions import db
        import uuid

        data = request.get_json()
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        amount = data.get('amount')
        description = data.get('description', '')

        if not from_user_id or not to_user_id or not amount:
            return jsonify({'success': False, 'message': 'Champs manquants'})

        if from_user_id == to_user_id:
            return jsonify({'success': False, 'message': 'Même utilisateur'})

        from_user = User.query.get(from_user_id)
        to_user = User.query.get(to_user_id)

        if not from_user or not to_user:
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'})

        from_wallet = Wallet.query.filter_by(user_id=from_user_id).first()
        to_wallet = Wallet.query.filter_by(user_id=to_user_id).first()

        if not from_wallet or from_wallet.balance_htg < amount:
            return jsonify({'success': False, 'message': 'Solde insuffisant'})

        # Effectuer le transfert
        from_wallet.balance_htg -= amount
        to_wallet.balance_htg += amount

        # Créer les transactions
        reference = f"TRF-{uuid.uuid4().hex[:8].upper()}"

        # Transaction sortante
        tx_out = Transaction(
            user_id=from_user_id,
            wallet_id=from_wallet.id,
            type='transfer_out',
            amount=amount,
            currency='HTG',
            status='completed',
            reference=reference,
            description=f'Transfert vers {to_user.first_name} {to_user.last_name} - {description}'
        )

        # Transaction entrante
        tx_in = Transaction(
            user_id=to_user_id,
            wallet_id=to_wallet.id,
            type='transfer_in',
            amount=amount,
            currency='HTG',
            status='completed',
            reference=reference,
            description=f'Transfert de {from_user.first_name} {from_user.last_name} - {description}'
        )

        db.session.add(tx_out)
        db.session.add(tx_in)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Transfert effectué', 'reference': reference})


    @app.route('/admin/users/add')
    @login_requis
    def admin_users_add():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('admin/admin_user_add.html')

    @app.route('/api/admin/users/add', methods=['POST'])
    @login_requis
    def api_admin_users_add():
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403

        from models import User, Wallet
        from extensions import db
        from werkzeug.security import generate_password_hash

        data = request.get_json()

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email déjà utilisé'})

        # Vérifier si le téléphone existe déjà
        if User.query.filter_by(phone=data['phone']).first():
            return jsonify({'success': False, 'message': 'Téléphone déjà utilisé'})

        # Créer l'utilisateur
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            password_hash=generate_password_hash(data['password']),
            is_admin=data.get('is_admin', False),
            is_agent=data.get('is_agent', False),

            is_verified=True,
            is_active=True

        )

        db.session.add(user)
        db.session.flush()

        # Créer son portefeuille
        wallet = Wallet(
            user_id=user.id,
            balance_htg=0,
            balance_usd=0
        )

        db.session.add(wallet)
        db.session.commit()

        # Email au nouvel utilisateur
        send_welcome_email(user)

        # Notification à l'admin
        notify_admin_new_user(user)

        return jsonify({'success': True, 'message': 'Utilisateur créé', 'user_id': user.id})



    @app.route('/api/admin/alerts')
    @login_requis
    def api_admin_alerts():
        if not session.get('is_admin'):
            return jsonify({'error': 'Non autorisé'}), 403

        from models import Deposit, Withdrawal, KYC

        pending_deposits = Deposit.query.filter_by(status='pending').count()
        pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()
        pending_kyc = KYC.query.filter_by(status='pending').count()

        # Utilisateurs signalés (à adapter selon ta logique)
        flagged_users = 0  # À implémenter selon tes besoins

        return jsonify({
            'pending_deposits': pending_deposits,
            'pending_withdrawals': pending_withdrawals,
            'flagged_users': flagged_users,
            'pending_kyc': pending_kyc
        })


    @app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
    @login_requis
    def api_update_user(user_id):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403

        from models import User
        from extensions import db

        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404

        data = request.get_json()

        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.phone = data.get('phone', user.phone)
        user.is_verified = data.get('is_verified', user.is_verified)
        user.is_active = data.get('is_active', user.is_active)
        user.is_admin = data.get('is_admin', user.is_admin)
        user.is_agent = data.get('is_agent', user.is_agent)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Utilisateur mis à jour'})

    @app.route('/admin/users')
    @login_requis
    def admin_users():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import User

        users = User.query.all()
        users_data = []

        for u in users:
            users_data.append({
                'id': u.id,
                'name': f"{u.first_name} {u.last_name}",
                'email': u.email,
                'phone': u.phone or '-',
                'is_admin': u.is_admin,
                'is_agent': u.is_agent,
                'is_verified': u.is_verified,
                'is_active': u.is_active,
                'created_at': u.created_at.strftime('%d/%m/%Y %H:%M') if u.created_at else 'Non disponible'
            })

        return render_template('admin_users.html', users=users_data)

    @app.route('/admin/agents')
    @login_requis
    def admin_agents():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        from models import User
        agents = User.query.filter_by(is_agent=True).all()

        agents_json = []

        for agent in agents:
            agents_json.append({
                "id": agent.id,
                "first_name": agent.first_name,
                "last_name": agent.last_name,
                "email": agent.email,
                "phone": agent.phone,
                "agent_code": agent.agent_code,
                "agent_balance": float(agent.agent_balance or 0),
                "created_at": agent.created_at.strftime("%d/%m/%Y") if agent.created_at else ""
            })

        return render_template(
            "admin_agents.html",
            agents=agents,
            agents_json=agents_json
        )

    @app.route('/admin/wallets')
    @login_requis
    def admin_wallets():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        from models import Wallet

        wallets = Wallet.query.all()

        wallets_json = []

        for w in wallets:
            wallets_json.append({
                "id": w.id,
                "user_id": w.user_id,
                "balance_htg": float(w.balance_htg or 0),
                "balance_usd": float(w.balance_usd or 0),
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
                "user": {
                    "first_name": w.user.first_name if w.user else "",
                    "last_name": w.user.last_name if w.user else "",
                    "email": w.user.email if w.user else "",
                    "phone": getattr(w.user, "phone", "")
                }
            })

        return render_template(
            'admin_wallets.html',
            wallets=wallets,
            wallets_json=wallets_json
        )

    @app.route('/admin/transactions')
    @login_requis
    def admin_transactions():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        transaction = Transaction()
        transactions = Transaction().get_all_transactions()
        return render_template('admin_transactions.html', transactions=transactions)

    @app.route('/admin/virtual-cards')
    @login_requis
    def admin_virtual_cards():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        from models import VirtualCard
        cards = VirtualCard.query.all()
        return render_template('admin_cards.html', cards=cards)

    @app.route('/admin/payments')
    @login_requis
    def admin_payments():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        from models import Payment
        payments = Payment.query.all()
        return render_template('admin_payments.html', payments=payments)

    @app.route('/admin/disputes')
    @login_requis
    def admin_disputes():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin_disputes.html')

    @app.route('/admin/audit-logs')
    @login_requis
    def admin_audit_logs():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        from models import AuditLog
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
        return render_template('admin_audit.html', logs=logs)

    @app.route('/admin/settings')
    @login_requis
    def admin_settings():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin_settings.html')

    @app.route('/api/admin/chart-data')
    @login_requis
    def api_admin_chart_data():
        if not session.get('is_admin'):
            return jsonify({'error': 'Non autorisé'}), 403

        from models import Transaction
        from datetime import datetime, timedelta

        # Derniers 30 jours
        labels = []
        volumes = []

        for i in range(7, -1, -1):
            date = datetime.now() - timedelta(days=i * 4)
            labels.append(date.strftime('%d %b'))

            # Calculer le volume pour cette période
            start_date = datetime.now() - timedelta(days=(i + 1) * 4)
            end_date = datetime.now() - timedelta(days=i * 4)

            volume = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.created_at >= start_date,
                Transaction.created_at < end_date,
                Transaction.status == 'completed'
            ).scalar() or 0

            volumes.append(float(volume) / 1000)  # Convertir en K

        return jsonify({
            'labels': labels,
            'volumes': volumes
        })

    @app.route('/admin/reports')
    @login_requis
    def admin_reports():
        if not session.get('is_admin'):
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('dashboard'))

        # Récupérer les transactions
        transactions = Transaction().get_all_transactions()  # Votre fonction DB
        users = Transaction().get_all_users()

        # Définir stats ICI avant de l'utiliser
        stats = {
            'total_volume': sum(t['amount'] for t in transactions),
            'total_transactions': len(transactions),
            'total_fees': sum(t['fee'] for t in transactions),
            'total_users': len(users),
            'pending_deposits': 0,
            'pending_withdrawals': 0
        }

        return render_template('admin/admin_reports.html',
                               reports=stats,
                               transactions=transactions,
                               users=users)

    @app.route('/terms')
    def terms():
        return render_template('terms.html')

    @app.route('/privacy')
    def privacy():
        return render_template('privacy.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    @app.route('/api/contact', methods=['POST'])
    def api_contact():
        from models import ContactMessage
        from extensions import db
        from datetime import datetime

        data = request.json

        message = ContactMessage(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            subject=data.get('subject'),
            message=data.get('message'),
            created_at=datetime.utcnow(),
            status='pending'
        )

        db.session.add(message)
        db.session.commit()

        # Option: envoyer un email
        print(f"📧 Nouveau message de {data.get('email')}: {data.get('subject')}")

        return jsonify({'success': True, 'message': 'Message envoyé'})

    def is_sanctioned(email=None, phone=None, full_name=None):
        """
        Vérifie si une personne est sur une liste de sanctions
        Retourne True si trouvé, False sinon
        """
        query = SanctionedPerson.query

        if email:
            if query.filter_by(email=email).first():
                return True

        if phone:
            if query.filter_by(phone=phone).first():
                return True

        if full_name:
            # Recherche approximative par nom
            if query.filter(SanctionedPerson.full_name.ilike(f"%{full_name}%")).first():
                return True

        return False

    def calculate_age(birth_date):
        """
        Calcule l'âge à partir d'une date de naissance

        Args:
            birth_date: date de naissance (objet datetime.date ou datetime.datetime)

        Returns:
            int: âge en années
        """
        if not birth_date:
            return 0

        today = datetime.utcnow().date()

        # Si birth_date est un datetime, le convertir en date
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()

        age = today.year - birth_date.year

        # Vérifier si l'anniversaire est déjà passé cette année
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1

        return max(0, age)  # Ne retourne jamais négatif


    # À vérifier avant d'approuver un agent
    def check_agent_eligibility(user):
        conditions = {
            'has_verified_kyc': user.is_verified == True,
            'has_valid_phone': user.phone and len(user.phone) >= 8,
            'has_valid_email': '@' in user.email,
            'is_active': user.is_active == True,
            'min_age': calculate_age(user.birth_date) >= 18 if user.birth_date else False,
            'no_sanctions': not is_sanctioned(user.email, user.phone),  # À implémenter
            'is_trusted': user.created_at < datetime.utcnow() - timedelta(days=30)  # Compte âgé de +30 jours
        }
        return all(conditions.values())

    @app.route('/api/agent/apply', methods=['POST'])
    @login_requis
    def agent_apply():
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        # Vérifier critères
        if not user.is_verified:
            return jsonify({'success': False, 'message': 'Vous devez d\'abord vérifier votre compte (KYC)'})

        if user.is_agent:
            return jsonify({'success': False, 'message': 'Vous êtes déjà agent'})

        # Vérifier si demande déjà envoyée
        existing = AgentApplication.query.filter_by(user_id=user_id, status='pending').first()
        if existing:
            return jsonify({'success': False, 'message': 'Vous avez déjà une demande en attente'})

        # Sauvegarder la demande
        application = AgentApplication(
            user_id=user_id,
            business_name=request.form.get('business_name'),
            business_address=request.form.get('business_address'),
            business_license=request.form.get('business_license'),
            business_type=request.form.get('business_type'),
            initial_capital=request.form.get('initial_capital'),
            desired_commission=request.form.get('desired_commission'),
            status='pending'
        )

        # Sauvegarder les documents
        files = request.files.getlist('documents')
        for file in files:
            filename = f"agent_{user_id}_{uuid.uuid4().hex[:8]}.pdf"
            file.save(f"uploads/agent_docs/{filename}")
            # Sauvegarder le chemin en DB

        db.session.add(application)
        db.session.commit()

        log_action(
            action="AGENT_REQUEST",
            user_id=user.id
        )

        send_agent_request_email(user)
        notify_admin_agent_request(user)

        return jsonify({'success': True, 'message': 'Candidature envoyée'})

    @app.route('/api/admin/users/<int:user_id>/resend-email', methods=['POST'])
    @admin_required
    def resend_email(user_id):

        user = User.query.get_or_404(user_id)

        send_welcome_email(user)

        return jsonify({
            "success": True,
            "message": "Email renvoyé"
        })

    @app.route('/resend-agent-email/<int:user_id>')
    def resend_agent_email(user_id):

        user = User.query.get_or_404(user_id)

        send_agent_request_email(user)

        return {
            "success": True,
            "message": "Email agent renvoyé"
        }

    @app.route('/admin/agent-applications')
    @login_requis
    def admin_agent_applications():
        if not session.get('is_admin'):
            return redirect(url_for('dashboard'))

        applications = AgentApplication.query.filter_by(status='pending').all()
        return render_template('admin_agent_applications.html', applications=applications)

    @app.route('/admin/reports/export')
    @login_requis
    def export_report():
        if not session.get('is_admin'):
            return jsonify({'error': 'Unauthorized'}), 403

        # Logique d'export CSV/PDF
        transactions = Transaction().get_all_transactions()

        # Créer CSV
        import csv
        from io import StringIO
        from flask import Response

        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'User', 'Amount', 'Date', 'Status'])

        for tx in transactions:
            cw.writerow([tx.id, tx.user_name, tx.amount, tx.created_at, tx.status])

        output = Response(si.getvalue(), mimetype='text/csv')
        output.headers["Content-Disposition"] = "attachment; filename=rapport_transactions.csv"

        return output

    @app.route('/api/log-click', methods=['POST'])
    @login_requis
    def log_click():
        data = request.json
        log = AuditLog(
            user_id=session.get('user_id'),
            action=f"click_{data.get('action')}",
            button_id=data.get('button_id'),
            page_url=data.get('page'),
            request_method='CLICK',
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})

    @app.route('/api/login-duration', methods=['POST'])
    @login_requis
    def log_duration():
        # À appeler avant logout
        duration = request.json.get('duration')  # en secondes
        log = AuditLog(
            user_id=session.get('user_id'),
            action='session_end',
            duration_ms=duration * 1000,
            request_data=f"Durée de session: {duration} secondes",
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})


    @app.route("/admin/partners")
    def admin_partners_page():
        return render_template("admin/partners.html")

    @app.route("/admin/login")
    def admin_login():
        return render_template("admin/admin_login.html")



    @app.route('/partner/dashboard')
    @login_requis
    @admin_required
    def partner_dashboard():
        """Dashboard partenaire"""
        from models import Partner, PartnerTransaction
        from datetime import datetime, timedelta
        from flask import session
        from extensions import db
        from sqlalchemy import func

        user_id = session.get("user_id")
        user = db.session.get(User, user_id)

        # Récupérer le partenaire
        partner = Partner.query.first()

        if not partner:
            flash('Aucun partenaire configuré', 'warning')
            return render_template('partner/dashboard.html', partner=None)

        # ========== STATISTIQUES RÉELLES ==========

        # Total transactions
        total_transactions = PartnerTransaction.query.filter_by(partner_id=partner.id).count()
        total_volume = db.session.query(func.sum(PartnerTransaction.amount)).filter_by(
            partner_id=partner.id, status='completed'
        ).scalar() or 0

        total_fees = db.session.query(func.sum(PartnerTransaction.fee)).filter_by(
            partner_id=partner.id, status='completed'
        ).scalar() or 0

        # Transactions du mois
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        monthly_transactions = PartnerTransaction.query.filter(
            PartnerTransaction.partner_id == partner.id,
            PartnerTransaction.created_at >= month_start,
            PartnerTransaction.status == 'completed'
        ).count()
        monthly_volume = db.session.query(func.sum(PartnerTransaction.amount)).filter(
            PartnerTransaction.partner_id == partner.id,
            PartnerTransaction.created_at >= month_start,
            PartnerTransaction.status == 'completed'
        ).scalar() or 0

        # Transactions du jour
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_transactions = PartnerTransaction.query.filter(
            PartnerTransaction.partner_id == partner.id,
            PartnerTransaction.created_at >= today_start,
            PartnerTransaction.status == 'completed'
        ).count()
        daily_volume = db.session.query(func.sum(PartnerTransaction.amount)).filter(
            PartnerTransaction.partner_id == partner.id,
            PartnerTransaction.created_at >= today_start,
            PartnerTransaction.status == 'completed'
        ).scalar() or 0

        # ========== GRAPHIQUE 30 JOURS ==========
        chart_labels = []
        chart_data = []
        for i in range(29, -1, -1):
            date = datetime.utcnow() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            chart_labels.append(date.strftime('%d/%m'))

            volume = db.session.query(func.sum(PartnerTransaction.amount)).filter(
                PartnerTransaction.partner_id == partner.id,
                PartnerTransaction.created_at >= day_start,
                PartnerTransaction.created_at < day_end,
                PartnerTransaction.status == 'completed'
            ).scalar() or 0
            chart_data.append(float(volume))

        # ========== RÉPARTITION PAR TYPE ==========
        type_data = db.session.query(
            PartnerTransaction.type,
            func.count(PartnerTransaction.id).label('count')
        ).filter(
            PartnerTransaction.partner_id == partner.id,
            PartnerTransaction.status == 'completed'
        ).group_by(PartnerTransaction.type).all()

        type_labels = [t[0] for t in type_data]
        type_counts = [t[1] for t in type_data]

        # ========== DERNIÈRES TRANSACTIONS ==========
        transactions = PartnerTransaction.query.filter_by(
            partner_id=partner.id
        ).order_by(
            PartnerTransaction.created_at.desc()
        ).limit(10).all()

        # ========== DERNIERS WEBHOOKS ==========
        webhooks = WebhookLog.query.filter_by(
            partner_id=partner.id
        ).order_by(
            WebhookLog.created_at.desc()
        ).limit(10).all()

        # ========== STATS POUR LE TEMPLATE ==========
        stats = {
            'total': {
                'volume': float(total_volume),
                'count': total_transactions,
                'fees': float(total_fees)
            },
            'monthly': {
                'volume': float(monthly_volume),
                'count': monthly_transactions,
                'limit': float(partner.monthly_limit) if partner.monthly_limit else 2000000,
                'remaining': max(0, float(partner.monthly_limit) - float(
                    monthly_volume)) if partner.monthly_limit else None
            },
            'daily': {
                'volume': float(daily_volume),
                'count': daily_transactions,
                'limit': float(partner.daily_limit) if partner.daily_limit else 500000,
                'remaining': max(0, float(partner.daily_limit) - float(daily_volume)) if partner.daily_limit else None
            },
            'rate_limit': {
                'minute': {'used': 12, 'limit': 60},
                'hour': {'used': 245, 'limit': 1000},
                'day': {'used': 1200, 'limit': 10000}
            }
        }

        return render_template('partner/dashboard.html',
                               partner=partner,
                               stats=stats,
                               chart_labels=chart_labels,
                               chart_data=chart_data,
                               type_labels=type_labels if type_labels else ['Aucune donnée'],
                               type_data=type_counts if type_counts else [1],
                               transactions=transactions,
                               webhooks=webhooks)

    @app.route('/partner/transactions')
    @login_requis
    def partner_transactions():
        """Liste des transactions du partenaire"""
        from models import Partner, PartnerTransaction
        from flask import request

        # Récupérer le partenaire
        partner = Partner.query.first()

        if not partner:
            flash('Aucun partenaire configuré', 'warning')
            return redirect(url_for('partner_dashboard'))

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Filtrer les transactions
        transactions = PartnerTransaction.query.filter_by(
            partner_id=partner.id
        ).order_by(
            PartnerTransaction.created_at.desc()
        ).paginate(page=page, per_page=per_page)

        # Statistiques
        from sqlalchemy import func
        total_volume = db.session.query(func.sum(PartnerTransaction.amount)).filter_by(
            partner_id=partner.id,
            status='completed'
        ).scalar() or 0

        total_count = PartnerTransaction.query.filter_by(partner_id=partner.id).count()
        pending_count = PartnerTransaction.query.filter_by(partner_id=partner.id, status='pending').count()

        return render_template('partner/transactions.html',
                               partner=partner,
                               transactions=transactions,
                               total_volume=total_volume,
                               total_count=total_count,
                               pending_count=pending_count,
                               page=page,
                               per_page=per_page)





    @app.route("/api/partner/admin/partners/<int:partner_id>/keys")
    def get_partner_keys(partner_id):
        api_key = PartnerAPIKey.query.filter_by(
            partner_id=partner_id,
            is_active=True
        ).first()

        if not api_key:
            return jsonify({"error": "No API key found"}), 404

        return jsonify({
            "client_id": api_key.client_id,
            "client_secret": api_key.secret_plain
        })

    @app.route("/api/partner/admin/partners/<int:partner_id>/toggle",
               methods=["POST"])
    def toggle_partner(partner_id):

        partner = Partner.query.get_or_404(partner_id)

        partner.is_active = not partner.is_active

        db.session.commit()

        return jsonify({
            "message": "Partner updated",
            "is_active": partner.is_active
        })

    # Version de test qui affiche l'email dans la console
    def send_partner_welcome_email_test(partner, client_id, client_secret):
        print("\n" + "=" * 60)
        print("📧 EMAIL DE BIENVENUE PARTENAIRE")
        print("=" * 60)
        print(f"À: {partner.contact_email}")
        print(f"Sujet: Bienvenue sur GmesPay - Vos identifiants d'intégration")
        print("-" * 60)
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret}")
        print(f"Nom: {partner.name}")
        print(f"Code: {partner.code}")
        print("=" * 60)


    @app.route('/logout')
    def logout():

        user_id = session.get('user_id')
        session_id = session.get('session_id')

        if user_id:
            log_action(
                action="LOGOUT",
                user_id=user_id,
                request_data={
                    "session_id": session_id
                }
            )

        session.clear()

        return redirect(url_for('index'))


    return app





if __name__ == '__main__':


    app = create_app(os.getenv('FLASK_ENV', 'development'))

    with app.app_context():
        create_admin_if_not_exists()

    # Démarrer sur le bon port pour Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)