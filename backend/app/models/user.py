from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # 1:1 with CandidateProfile
    profile = relationship(
        "CandidateProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
