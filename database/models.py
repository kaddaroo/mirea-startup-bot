from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    surname = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    patronymic = Column(String(255), nullable=True)
    id_university = Column(Integer, nullable=True)
    group_name = Column(String(255), nullable=True)
    coins = Column(Integer, default=0)
    institute = Column(String(255), nullable=True)
    direction_code = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column("UPD", DateTime, onupdate=func.now())


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), index=True)
    event_code = Column(String(100), index=True)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), index=True)
    event_code = Column(String(100), index=True)
    status = Column(String(50))
