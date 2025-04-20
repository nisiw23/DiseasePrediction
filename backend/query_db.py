from sqlalchemy import create_engine, text
from database.db import engine

with engine.begin() as conn:
    print("\nDiseases:")
    for row in conn.execute(text("SELECT * FROM diseases")).mappings():
        print(dict(row))
    
    print("\nModels:")
    for row in conn.execute(text("SELECT * FROM models")).mappings():
        print(dict(row))
    
    print("\nPatients:")
    for row in conn.execute(text("SELECT * FROM Patients")).mappings():
        print(dict(row))

    print("\ncsv_uploads:")
    for row in conn.execute(text("SELECT * FROM csv_uploads")).mappings():
        print(dict(row))
