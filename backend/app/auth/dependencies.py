from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.retailer import Retailer
from app.auth.jwt_handler import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_retailer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Retailer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    retailer_id = verify_token(token)
    if retailer_id is None:
        raise credentials_exception

    retailer = (
        db.query(Retailer)
        .filter(Retailer.id == retailer_id, Retailer.is_active == True)
        .first()
    )
    if retailer is None:
        raise credentials_exception

    return retailer
