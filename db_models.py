from sqlalchemy import Column, Integer, String
from db_connect import Base


class Image(Base):
    __tablename__ = 'images'

    req_code = Column(Integer, unique=False)
    name = Column(String, primary_key=True)
    exist_time = Column(String)
