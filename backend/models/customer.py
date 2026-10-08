from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    id: Optional[int]
    name: str
    email: str
    marketing_consent: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'marketing_consent': self.marketing_consent,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
        }


@dataclass
class AccessSession:
    id: Optional[int]
    customer_id: int
    ip_address: str
    session_token: str
    authenticated: bool
    expires_at: str
    created_at: Optional[str] = None

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'ip_address': self.ip_address,
            'session_token': self.session_token,
            'authenticated': self.authenticated,
            'expires_at': str(self.expires_at),
            'created_at': str(self.created_at) if self.created_at else None,
        }
