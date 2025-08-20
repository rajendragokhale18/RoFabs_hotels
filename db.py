import pyodbc
import pickle
import numpy as np


def get_db_connection():
    try:
        # Connection parameters
        server = "rfbs.czc28wscwu15.eu-north-1.rds.amazonaws.com"
        database = "pms"
        username = "admin"
        password = "Rofabs1234"

        # Create connection string
        conn_str = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}"
        )

        # Establish connection
        conn = pyodbc.connect(conn_str)
        print("Successfully connected to database")
        return conn

    except pyodbc.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def create_tables():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Create face_encodings table if it doesn't exist
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='face_encodings' AND xtype='U')
                CREATE TABLE face_encodings (
                    id VARCHAR(255) PRIMARY KEY,
                    encoding VARBINARY(MAX) NOT NULL
                )
            """)
            conn.commit()
            print("Tables created successfully")
        except pyodbc.Error as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()


class FaceEncoding:
    def __init__(self, id=None, encoding=None):
        self.id = id
        self._encoding = encoding

    @property
    def encoding(self):
        if self._encoding:
            return pickle.loads(self._encoding)
        return None

    @encoding.setter
    def encoding(self, value):
        if value is not None:
            self._encoding = pickle.dumps(value)
        else:
            self._encoding = None


def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()


# Create tables on module import
create_tables()
