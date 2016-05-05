from sqlalchemy import text
from app import db

def existing_pool_membership(vms):
  sql = text('SELECT COUNT(*) FROM name from blah')
  result = db.engine.execute(sql)
  names = []
  for row in result:
    names.append(row[0])


