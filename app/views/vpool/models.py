from app import db
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import InputRequired

class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
  cluster = db.relationship('Cluster', backref=db.backref('cluster', lazy='dynamic'))

  def __init__(self, id=None, name=None, cluster_id=None, cluster=None):
    self.id = id
    self.name = name
    self.cluster_id = cluster_id
    self.cluster = cluster

  def get_memberships(self):
    return db.session.query(PoolMembership).join(
      PoolMembership.pool, aliased=True).filter_by(id=self.id).all()

  @staticmethod
  def get_all(cluster):
    return db.session.query(VirtualMachinePool).join(
      VirtualMachinePool.cluster, aliased=True).filter_by(id=cluster.id)


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

  @staticmethod
  def get_all(zone):
    return db.session.query(PoolMembership).join(
      PoolMembership.pool, aliased=True).filter_by(zone=zone)


class CreateVmForm(Form):
  hostname = StringField('Hostname', [InputRequired()], default='<somename>.log82.altus.bblabs')
  cpu = StringField('CPU', [InputRequired()], default='.25')
  vcpu = StringField('VCPU', [InputRequired()], default='1')
  memory_megabytes = StringField('Memory (MB)', [InputRequired()], default='2048')