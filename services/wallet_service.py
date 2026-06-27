# services/wallet_service.py

class WalletService:

    @staticmethod
    def credit_htg(wallet, amount):

        wallet.balance_htg += amount

        return wallet

    @staticmethod
    def debit_htg(wallet, amount):

        if wallet.balance_htg < amount:

            raise Exception(
                "Solde insuffisant"
            )

        wallet.balance_htg -= amount

        return wallet

class TransferService:

    @staticmethod
    def transfer_htg(
        sender_wallet,
        receiver_wallet,
        amount
    ):

        if sender_wallet.balance_htg < amount:
            raise Exception(
                "Solde insuffisant"
            )

        sender_wallet.balance_htg -= amount

        receiver_wallet.balance_htg += amount