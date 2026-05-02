from database import Base, engine
import models 


Base.metadata.drop_all(bind=engine)   # 🔥 drops all tables
Base.metadata.create_all(bind=engine) # 🔥 recreates them

print(engine.url)