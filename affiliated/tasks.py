from datetime import datetime, timedelta
from database import SessionLocal
from affiliated import models
from sqlalchemy import cast, Date


def deactivate_affiliate_code_expire():
    db = SessionLocal()
    today_date = datetime.utcnow() - timedelta(days=1)
    AffiliateInDb = (
        db.query(models.Affiliate).
        filter(cast(models.Affiliate.end_date, Date) == today_date.date()).all()
    )
    for affiliate in AffiliateInDb:
        affiliate.is_active = False
        db.commit()
    print("Expiring affiliate links are deactivate.")
    return True



