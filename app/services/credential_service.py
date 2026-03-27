import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.data.db.models.credential_link import CredentialLinkModel


class CredentialService:
    def __init__(self, session: Session):
        self.session = session

    def create_link(self, order_item_id: str, credentials: dict,
                    ttl_hours: int = 48) -> tuple[CredentialLinkModel, str]:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        model = CredentialLinkModel(
            id=str(uuid.uuid4()),
            order_item_id=order_item_id,
            token_hash=token_hash,
            credentials=credentials,
            expires_at=now + timedelta(hours=ttl_hours),
            is_consumed=False,
        )
        self.session.add(model)
        self.session.commit()
        return model, token

    def retrieve_credentials(self, token: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        link = self.session.query(CredentialLinkModel).filter_by(
            token_hash=token_hash
        ).first()

        if link is None:
            raise self.LinkNotFoundError("Credential link not found.")

        if link.is_consumed:
            raise self.LinkConsumedError("Credential link already consumed.")

        now = datetime.now(timezone.utc)
        if link.expires_at <= now:
            raise self.LinkExpiredError("Credential link has expired.")

        link.is_consumed = True
        link.accessed_at = now
        self.session.commit()

        return {
            "credentials": link.credentials,
            "accessed_at": link.accessed_at.isoformat(),
        }

    class LinkExpiredError(Exception):
        pass

    class LinkConsumedError(Exception):
        pass

    class LinkNotFoundError(Exception):
        pass
