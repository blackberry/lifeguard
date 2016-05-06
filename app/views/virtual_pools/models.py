from app import db


class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  zone_number = db.Column(db.Integer, db.ForeignKey('zone.number'), nullable=False, )
  zone = db.relationship('Zone', backref=db.backref('zone', lazy='dynamic'))
  cluster_id = db.Column(db.Integer, nullable=False)

  def __init__(self, id=None, name=None, zone_number=None, cluster_id=None):
    self.id = id
    self.name = name
    self.zone_number = zone_number
    self.cluster_id = cluster_id


class PoolMembership(db.Model):
  vm_id = db.Column(db.Integer, primary_key=True)
  pool_id = db.Column(db.Integer, db.ForeignKey('virtual_machine_pool.id'), primary_key=True)
  pool = db.relationship('VirtualMachinePool', backref=db.backref('virtual_machine_pool', lazy='dynamic'))
  date_added = db.Column(db.DateTime, nullable=False)

  def __init__(self, pool_id=None, pool=None, vm_id=None, date_added=None):
    self.pool_id = pool_id
    self.pool = pool
    self.vm_id = vm_id
    self.date_added = date_added
