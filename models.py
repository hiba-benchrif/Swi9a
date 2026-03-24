from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prix_publics = relationship("PrixPublic", back_populates="user")
    depenses = relationship("Depense", back_populates="user")


class PrixPublic(Base):
    __tablename__ = "prix_public"

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    city = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="prix_publics")


class Depense(Base):
    __tablename__ = "depenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    category = Column(String, index=True, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="depenses")
