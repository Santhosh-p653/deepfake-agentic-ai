import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
<<<<<<< Updated upstream

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def check_db_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except SQLAlchemyError:
        return False
=======
DATABASE_URL=os.getenv("DATABASE_URL")
engine=create_engine(DATABASE_URL)
def check_db_connection():
	try:
		with engine.connect() as connection:
		connection.execute(text("SELECT 1"))
		return True
		print("Database Connection Success")
		connection.close()
	except SQLAlchemyError as e:
		print("Database Connection Failed")
		print(str(e))
		return False
>>>>>>> Stashed changes
