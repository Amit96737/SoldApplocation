
from fastapi import HTTPException
from googleapiclient.discovery import build
from google.oauth2 import service_account
from constants import GOOGLE_PLAY_CREDENTIALS_PATH

print("GOOGLE_PLAY_CREDENTIALS_PATH", GOOGLE_PLAY_CREDENTIALS_PATH)

def validate_google_receipt(package_name: str, product_id: str, purchase_token: str) -> dict:
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_PLAY_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    service = build("androidpublisher", "v3", credentials=credentials)
    try:
        result = (
            service.purchases()
            .subscriptions()
            .get(packageName=package_name, subscriptionId=product_id, token=purchase_token)
            .execute()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google receipt validation failed: {str(e)}")

    