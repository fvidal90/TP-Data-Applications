import os

from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Boolean
from sqlalchemy.orm import declarative_base


PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DB = os.getenv("PG_DB")
URI = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"


Base = declarative_base()


class DelayMetrics(Base):
    """Delay metrics data model."""
    __tablename__ = "delay_metrics"
    fl_date = Column(Date, primary_key=True)
    origin = Column(String, primary_key=True)
    dep_delay_mean = Column(Float)
    dep_delay_count = Column(Integer)


class DelayAnomalies(Base):
    """Delay anomalies data model."""
    __tablename__ = "delay_anomalies"
    fl_date = Column(Date, primary_key=True)
    origin = Column(String, primary_key=True)
    anomaly = Column(Boolean)


def main():
    """Program entrypoint."""
    engine = create_engine(URI, echo=True)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    main()
