# services/cash_service.py
from extensions import db
from models import User, Agent, CashDeposit, Wallet, Transaction, AuditLog
from utils.helpers import generate_reference
from datetime import datetime
from flask import current_app


class CashService:

    @staticmethod
    def get_nearby_agents(latitude=None, longitude=None, limit=10):
        """Récupérer les agents à proximité"""
        agents = Agent.query.filter_by(is_active=True).all()

        # En attendant une vraie géolocalisation
        agents_list = [{
            'id': a.id,
            'agent_code': a.agent_code,
            'business_name': a.business_name,
            'business_address': a.business_address,
            'phone': a.phone,
            'commission_rate': float(a.commission_rate)
        } for a in agents]

        return agents_list

    @staticmethod
    def initiate_cash_deposit(user_id, amount, agent_code):
        """Initier un dépôt cash"""
        # Vérifier l'agent
        agent = Agent.query.filter_by(agent_code=agent_code, is_active=True).first()
        if not agent:
            raise Exception("Agent invalide ou inactif")

        # Vérifier le montant
        if amount < 100:
            raise Exception("Montant minimum: 100 HTG")
        if amount > 50000:
            raise Exception("Montant maximum: 50,000 HTG")

        # Calculer les frais
        fee = amount * (float(agent.commission_rate) / 100)
        net_amount = amount - fee

        # Générer référence
        reference = generate_reference('CASH')

        # Créer le dépôt
        cash_deposit = CashDeposit(
            user_id=user_id,
            agent_id=agent.id,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            reference=reference,
            agent_code_used=agent_code,
            status='pending'
        )
        db.session.add(cash_deposit)
        db.session.commit()

        return {
            'deposit_id': cash_deposit.id,
            'reference': reference,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'agent': {
                'name': agent.business_name,
                'address': agent.business_address,
                'phone': agent.phone
            },
            'instructions': f"Présentez-vous chez l'agent avec la référence {reference}"
        }

    @staticmethod
    def confirm_cash_deposit(agent_id, reference):
        """Agent confirme le dépôt"""
        cash_deposit = CashDeposit.query.filter_by(reference=reference, status='pending').first()

        if not cash_deposit:
            raise Exception("Dépôt non trouvé")

        # Vérifier que l'agent est le bon
        if cash_deposit.agent_id != agent_id:
            raise Exception("Vous n'êtes pas l'agent assigné à ce dépôt")

        # Créditer le wallet de l'utilisateur
        wallet = Wallet.query.filter_by(user_id=cash_deposit.user_id).first()
        if not wallet:
            raise Exception("Wallet utilisateur non trouvé")

        wallet.balance_htg += cash_deposit.net_amount

        # Créditer le compte de l'agent (commission)
        agent = Agent.query.get(agent_id)
        if agent:
            agent.balance_htg += cash_deposit.fee

        # Transaction
        transaction = Transaction(
            user_id=cash_deposit.user_id,
            wallet_id=wallet.id,
            type='deposit',
            amount=cash_deposit.amount,
            fee=cash_deposit.fee,
            currency='HTG',
            status='completed',
            reference=cash_deposit.reference,
            description=f"Dépôt cash chez {agent.business_name}"
        )
        db.session.add(transaction)

        # Mettre à jour le dépôt
        cash_deposit.status = 'completed'
        cash_deposit.verified_by_agent = True
        cash_deposit.verified_at = datetime.utcnow()
        cash_deposit.completed_at = datetime.utcnow()

        # Audit
        audit = AuditLog(
            user_id=cash_deposit.user_id,
            action='cash_deposit_completed',
            ip_address='agent_system'
        )
        db.session.add(audit)

        db.session.commit()

        return {
            'message': 'Dépôt confirmé',
            'reference': reference,
            'amount': float(cash_deposit.net_amount)
        }