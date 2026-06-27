# test.py
from app import create_app
from extensions import db
from models import Partner

app = create_app('development')

with app.app_context():
    partners = Partner.query.all()
    print(f"Nombre de partenaires: {len(partners)}")
    for p in partners:
        print(f"- {p.id}: {p.name} ({p.code})")

    if len(partners) == 0:
        print("❌ Aucun partenaire trouvé")
    else:
        print("✅ Partenaires trouvés")