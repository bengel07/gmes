

from flask import current_app
from datetime import datetime
import stripe

class CardService:

    def get_stripe(self):
        stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
        return stripe

    def create_cardholder(self, user):
        """Créer un cardholder Stripe pour l'utilisateur"""
        try:
            cardholder = stripe.issuing.Cardholder.create(
                type='individual',
                name=f"{user.first_name} {user.last_name}",
                email=user.email,
                phone_number=user.phone,
                billing={
                    'address': {
                        'line1': 'Address line 1',
                        'city': 'Port-au-Prince',
                        'country': 'HT',
                        'postal_code': 'HT6110'
                    }
                },
                metadata={
                    'user_id': user.id,
                    'platform': 'GmesPay'
                }
            )
            return cardholder
        except Exception as e:
            current_app.logger.error(f"Stripe cardholder error: {str(e)}")
            raise Exception("Failed to create cardholder")

    def issue_virtual_card(self, user_id, user, cardholder_id=None):
        """Émettre une carte virtuelle"""
        try:
            if not cardholder_id:
                cardholder = self.create_cardholder(user)
                cardholder_id = cardholder.id

            # Créer la carte virtuelle
            card = stripe.issuing.Card.create(
                cardholder=cardholder_id,
                currency='usd',
                type='virtual',
                spending_controls={
                    'allowed_categories': ['all'],
                    'blocked_categories': ['cash_withdrawal'],
                    'spending_limits': [{
                        'amount': 5000,
                        'interval': 'monthly'
                    }]
                },
                metadata={
                    'user_id': user_id,
                    'platform': 'GmesPay'
                }
            )

            return {
                'card_id': card.id,
                'last4': card.last4,
                'brand': card.brand,
                'exp_month': card.exp_month,
                'exp_year': card.exp_year,
                'cvv': card.cvc,  # Note: à montrer une seule fois
                'status': card.status
            }

        except Exception as e:
            current_app.logger.error(f"Stripe card issuance error: {str(e)}")
            raise Exception("Failed to issue virtual card")

    def get_card_details(self, card_id):
        """Obtenir les détails d'une carte"""
        try:
            card = stripe.issuing.Card.retrieve(card_id)
            return {
                'last4': card.last4,
                'brand': card.brand,
                'exp_month': card.exp_month,
                'exp_year': card.exp_year,
                'status': card.status,
                'spending_controls': card.spending_controls
            }
        except Exception as e:
            current_app.logger.error(f"Stripe card retrieval error: {str(e)}")
            raise Exception("Failed to retrieve card details")

    def block_card(self, card_id):
        """Bloquer une carte"""
        try:
            card = stripe.issuing.Card.modify(
                card_id,
                status='blocked'
            )
            return {'status': card.status}
        except Exception as e:
            current_app.logger.error(f"Stripe card block error: {str(e)}")
            raise Exception("Failed to block card")