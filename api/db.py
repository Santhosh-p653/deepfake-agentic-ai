from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL=os.getenv("DATABASE_URL")
engine=create_engine(DATABASE_URL)
def check_db_connection:
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
