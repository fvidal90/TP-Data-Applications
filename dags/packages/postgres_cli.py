"""Implements a client class to interact with Postgres DB."""
import pandas as pd
from sqlalchemy import create_engine


class PostgresClient:
    """Class to connect to a Postgres DB using SQLAlchemy.

    Attributes
    ----------
        host: str
            Dns name of the host of the postgres database.
        port: int
            Port where the postgres database is listening.
        user: str
            Username to connect to the postgres database.
        password: str
            Password for this username.
        database: str
            Database to connect.
    """

    def __init__(self, host, port, user, password, database):
        """Constructor method for this class.

        Parameters
        ----------
            host: str
                Dns name of the host of the postgres database.
            port: int
                Port where the postgres database is listening.
            user: str
                Username to connect to the postgres database.
            password: str
                Password for this username.
            database: str
                Database to connect.
        """
        self.db = f"//{user}:{password}@{host}:{port}/{database}"
        self._engine = None

    def _get_engine(self):
        """Creates engine to connect to DB.

        Returns
        -------
            Engine: object
                Manages DB connections.
        """
        db_uri = f"postgresql:{self.db}"
        if not self._engine:
            self._engine = create_engine(db_uri)
        return self._engine

    def _connect(self):
        """Connects to DB.

        Returns
        -------
            Connection: object
                Proxy object for DB connections.
        """
        return self._get_engine().connect()

    @staticmethod
    def _cursor_columns(cursor):
        """Gets cursor columns.

        Parameters
        ----------
            cursor: object
                DB cursor.
        Returns
        -------
            list:
                List of columns.
        """
        if hasattr(cursor, "keys"):
            return cursor.keys()
        return [c[0] for c in cursor.description]

    def execute(self, sql, connection=None):
        """Executes SQL query.

        Parameters
        ----------
            sql: str
                Represents a query.
            connection: object
                Proxy for DB connection.
        Returns
        -------
            ResultProxy: object
                DB cursor object to provide access to row columns.
        """
        if connection is None:
            connection = self._connect()
        return connection.execute(sql)

    def insert_from_frame(self, df, table, if_exists="append", index=False, **kwargs):
        """Inserts a pandas DataFrame into the DB.

        Parameters
        ----------
            df: pandas.DataFrame
                Data to be inserted into the DB.
            table: str
                Table where DataFrame is inserted.
            if_exists: {"append", "fails", "replace"}
                What to do in case that the table already exists in DB.
            index: bool
                Whether to consider the DataFrame index as a column or not.
        """
        connection = self._connect()
        with connection:
            df.to_sql(table, connection, if_exists=if_exists, index=index, **kwargs)

    def to_frame(self, *args, **kwargs):
        """Executes a SQL query and returns a DataFrame.

        Returns
        -------
            df: pandas.DataFrame
                Result of the query in a pandas DataFrame.
        """
        cursor = self.execute(*args, **kwargs)
        if not cursor:
            df = pd.DataFrame()
            return df
        data = cursor.fetchall()
        if data:
            df = pd.DataFrame(data, columns=self._cursor_columns(cursor))
        else:
            df = pd.DataFrame()
        return df
