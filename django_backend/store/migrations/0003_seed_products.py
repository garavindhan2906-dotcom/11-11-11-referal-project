from django.db import migrations


PRODUCTS = [
    {"id": 1, "name": "KLEOMA", "for_gender": "male", "intent": "Love & Attraction", "emoji": "🌹", "price": 1234, "in_stock": True,
     "description": "A ritual-infused attar to support emotional connection, attraction, and presence. Velvety, warm, and floral — a blooming heart of rose and ylang ylang over soft musk and amber."},
    {"id": 2, "name": "KLINFON", "for_gender": "male", "intent": "Relaxation & Calm", "emoji": "🌿", "price": 1234, "in_stock": False,
     "description": "Supports calm presence and smooth transition into rest. Herbal and grounding — a sacred oil for those who need to still the mind and restore balance."},
    {"id": 3, "name": "MYSTRA", "for_gender": "male", "intent": "Financial Clarity", "emoji": "⚖️", "price": 1234, "in_stock": True,
     "description": "For financial clarity, balance, and mindful decision-making. Opens with zesty citrus and saffron, grounded by oud, amber, and sacred resins."},
    {"id": 4, "name": "SHREEMSRI", "for_gender": "male", "intent": "Wealth & Prosperity", "emoji": "👑", "price": 1234, "in_stock": True,
     "description": "Earthy, warm, and rich with subtle spice. A sacred oil for those walking the path of meaningful wealth creation — abundance, expansion, conscious prosperity."},
    {"id": 5, "name": "SUKCE", "for_gender": "male", "intent": "Success & Achievement", "emoji": "🏆", "price": 1234, "in_stock": True,
     "description": "A sensory anchor for entrepreneurs, leaders, and creators. Supports focus, discipline, and the unwavering belief that your success is inevitable."},
    {"id": 6, "name": "KAMAVYA", "for_gender": "female", "intent": "Attraction & Love", "emoji": "🌸", "price": 1234, "in_stock": True,
     "description": "Romantic and magnetic. A sweet whisper of almond into lush jasmine and crystal tuberose, settling into tonka bean and cocoa."},
    {"id": 7, "name": "KLINFON", "for_gender": "female", "intent": "Relaxation & Calm", "emoji": "🌙", "price": 1234, "in_stock": False,
     "description": "Encourages ease, softness, and balanced rhythm between activity and restoration. A sacred oil to transition into deep rest and inner stillness."},
    {"id": 8, "name": "HREMAAN", "for_gender": "female", "intent": "Financial Clarity", "emoji": "✨", "price": 1234, "in_stock": True,
     "description": "A sacred anchor for clarity in financial thinking, calm steady awareness, and balanced mindful decisions for women walking with abundance."},
    {"id": 9, "name": "SHRIVAA", "for_gender": "female", "intent": "Wealth & Prosperity", "emoji": "💛", "price": 1234, "in_stock": True,
     "description": 'Earthy, warm, and rich. "The scent is soft, but the impact is loud." For those walking the path of conscious prosperity — abundance in every drop.'},
    {"id": 10, "name": "YCNEX", "for_gender": "female", "intent": "Confidence & Success", "emoji": "⭐", "price": 1234, "in_stock": True,
     "description": "A sensory anchor for the woman who leads, creates, and rises. Focus, mental clarity, confident personal presence, consistent intentional action."},
    {"id": 11, "name": "KLINFON Combo", "for_gender": "combo", "intent": "Relaxation — Him & Her", "emoji": "🤍", "price": 2345, "in_stock": True,
     "description": "The complete KLINFON ritual set. Two complementary formulations for couples or for those who hold both energies — sacred shared rest."},
    {"id": 12, "name": "Love Combo", "for_gender": "combo", "intent": "Love & Attraction — Him & Her", "emoji": "💕", "price": 2345, "in_stock": True,
     "description": "The sacred love pairing — KLEOMA for him and KAMAVYA for her. One intention: to draw love closer and magnetise meaningful connections."},
]


def seed_products(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    for p in PRODUCTS:
        Product.objects.update_or_create(id=p["id"], defaults={
            "name": p["name"],
            "intent": p["intent"],
            "description": p["description"],
            "price": p["price"],
            "for_gender": p["for_gender"],
            "emoji": p["emoji"],
            "in_stock": p["in_stock"],
        })


def unseed_products(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    Product.objects.filter(id__in=[p["id"] for p in PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_product_image_product_video'),
    ]

    operations = [
        migrations.RunPython(seed_products, unseed_products),
    ]
