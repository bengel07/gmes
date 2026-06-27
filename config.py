import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail


class Config:
    # Flask
    SECRET_KEY = os.getenv( "SECRET_KEY")

    GMESPAY_PUBLIC_KEY = os.getenv("GMESPAY_PUBLIC_KEY")
    GMESPAY_SECRET_KEY = os.getenv("GMESPAY_SECRET_KEY")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

    # Database - FORCER SQLITE
    SQLALCHEMY_DATABASE_URI = 'sqlite:///gmespay.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Ajouter dans config.py
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')



    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # MonCash
    MONCASH_CLIENT_ID = os.getenv('MONCASH_CLIENT_ID')
    MONCASH_CLIENT_SECRET = os.getenv('MONCASH_CLIENT_SECRET')
    MONCASH_API_URL = os.getenv('MONCASH_API_URL', 'https://sandbox.moncashht.com/v1')
    MONCASH_WEBHOOK_SECRET = os.getenv('MONCASH_WEBHOOK_SECRET')

    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # ============ EMAIL CONFIGURATION ============
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'betterdeal3@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', ('GmesPay', 'betterdeal3@gmail.com'))

    # Uploads
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Fees
    DEPOSIT_FEE_MONCASH = 2.0
    WITHDRAWAL_FEE = 1.5
    INTERNATIONAL_PAYMENT_FEE = 1.0
    VIRTUAL_CARD_ISSUE_FEE = 3.0
    VIRTUAL_CARD_MONTHLY_FEE = 1.0

    # Limits
    MAX_DEPOSIT_AMOUNT = 1000
    MAX_WITHDRAWAL_AMOUNT = 500
    DAILY_TRANSACTION_LIMIT = 2000
    MONTHLY_TRANSACTION_LIMIT = 10000

    # KYC
    KYC_REQUIRED_FOR_CARD = True
    KYC_REQUIRED_FOR_WITHDRAWAL = True


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}