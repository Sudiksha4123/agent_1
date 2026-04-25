from database import Base, engine
import models  # register models

Base.metadata.create_all(bind=engine)