from database import SessionLocal
from datetime import datetime
from . import models


def deactivate_expired_item_boosts():
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()

        # Find expired boosts that are still active
        expired_boosts = (
            db.query(models.ItemBoost)
            .filter(
                models.ItemBoost.end_at <= current_time,
                models.ItemBoost.is_active == True
            )
            .all()
        )

        for boost in expired_boosts:
            boost.is_active = False
            shop_item = db.query(models.ShopItem).filter(
                models.ShopItem.id == boost.shop_item_id
            ).first()
            if shop_item:
                shop_item.is_boosted = False

        db.commit()
        print(f"Deactivated {len(expired_boosts)} expired item boosts.")
        return True

    except Exception as e:
        db.rollback()
        print(f"Error deactivating expired item boosts: {str(e)}")
        return False
    finally:
        db.close()

