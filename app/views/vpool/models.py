from flask import flash
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import InputRequired
from sqlalchemy import text

from app.views.zone.models import Zone
from app.views.cluster.models import Cluster

from app import db


class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  cluster_id = db.Column(db.Integer,  nullable=False)
  zone_number = db.Column(db.Integer,  nullable=False)

  #cluster = db.relationship('Cluster', primaryjoin=cluster_id==Cluster.id and zone_number==Cluster.zone_number, foreign_keys=[cluster_id, zone_number])

  #and_(A.b_id == B.id, A.id == C.a_id)
  cluster = db.relationship(
    'Cluster',
    primaryjoin="and_(VirtualMachinePool.cluster_id == Cluster.id, VirtualMachinePool.zone_number == Cluster.zone_number)",
    foreign_keys=[cluster_id, zone_number])

  #db.ForeignKeyConstraint(['cluster_id', 'zone_number'], ['cluster.id', 'cluster.zone_number'])

  def __init__(self, id=None, name=None, zone_number=None, cluster_id=None):
    self.id = id
    self.name = name
    self.cluster_id = cluster_id
    self.zone_number = zone_number

  def get_memberships(self):
    return db.session.query(PoolMembership).join(
      PoolMembership.pool, aliased=True).filter_by(id=self.id).all()

  def get_cluster(self):
    return Cluster.query.filter_by(zone_number=self.zone_number, id=self.cluster_id).first()

  @staticmethod
  def get_all(cluster):
    return db.session.query(VirtualMachinePool).filter_by(cluster_id=cluster.id,
                                                          zone_number=cluster.zone.number)

  @staticmethod
  def get_by_id_deprecated(id):
    """
    Performing a VirtualMachinePool.query.get(id) on a pool with
    where the cluster id exists more than once wasn't working

    So--instead of figuring out why my cluster/zone foreign key
    implementations in sqlalchemy return the wrong cluster
    I'll just do this myself.

       TODO: fix the model foreign key references/constraints properly
       TODO: Figure out why this needs to go in a no_autoflush block

    :param id:
    :return:
    """
    pool = None
    with db.session.no_autoflush:
      sql = text('select id, name, cluster_id, zone_number from virtual_machine_pool where id={}'.format(id))
      result = db.engine.execute(sql)
      row = result.first()
      zone = Zone.query.get(row['zone_number'])
      cluster = Cluster.query.filter_by(zone=zone, id=row['cluster_id']).first()
      print(cluster)

      #pool = VirtualMachinePool.query.filter_by(cluster=cluster, id=row['id']).first()
      pool = VirtualMachinePool.query.filter_by(cluster_id=cluster.id, zone_number=cluster.zone_number, id=row['id']).first()


      # cluster = Cluster.query.filter_by(zone=zone, id=row['cluster_id']).first()
      # print(cluster)
      # for field in row:
      #   print("here's: {}".format(field))
      # pool = VirtualMachinePool(
      #   id=row['id'],
      #   name=row['name'],
      #   cluster_id=cluster.id,
      #   zone_number=zone.number,
      #   zone=zone,
      #   cluster=cluster)
    return pool

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
