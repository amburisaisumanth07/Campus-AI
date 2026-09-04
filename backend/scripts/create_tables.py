import sys
sys.path.insert(0, r"c:\projects AI\campusAI")

from backend.app.db.session import engine
from backend.app.db.models import Base

def create_tables():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()
