
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy import DateTime, Column, Integer, String, Date, Boolean, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped

# Data_Conn = Shared_Database_Connection()
METADATA = MetaData()
BASE = declarative_base(metadata=METADATA)
ENGINE = create_engine("sqlite:///data/data.sqlite")


class Movie_DB(BASE):
    __tablename__ = 'movie'
    key = Column(String, primary_key=True)
    title = Column(String)
    active: Mapped[bool]
    is_played = Column(Boolean)
    added_at = Column(DateTime)
    updated_at = Column(DateTime)
    json_data = Column(JSON)


class Show_DB(BASE):
    __tablename__ = 'show'
    key = Column(String, primary_key=True)
    title = Column(String)
    active: Mapped[bool]
    is_played = Column(Boolean)
    added_at = Column(DateTime)
    updated_at = Column(DateTime)
    json_data = Column(JSON)


METADATA.create_all(ENGINE)
