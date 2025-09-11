from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def make_engine(db_uri: str, echo: bool):
    return create_engine(db_uri, echo=echo, future=True)

def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
