"""Create a business and print its API key:  python -m app.create_business "Acme Shop" """
import sys

from . import db

db.init_db()
name = " ".join(sys.argv[1:]) or "Demo Shop"
print(f"Business: {name}")
print(f"API key:  {db.create_business(name)}")
