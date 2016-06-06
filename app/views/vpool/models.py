from flask_wtf import Form
from wtforms import TextAreaField, StringField
from wtforms.validators import InputRequired
from app.views.cluster.models import Cluster
from app import db
from app.one import OneProxy
from app.one import INCLUDING_DONE
import re

class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  cluster_id = db.Column(db.Integer,  nullable=False)
  zone_number = db.Column(db.Integer,  nullable=False)
  template = db.Column(db.Text(), default='{% extends cluster.template %}')
  vars = db.Column(db.Text(), default='')
  cardinality = db.Column(db.Integer, nullable=False, default=1)
  cluster = db.relationship(
    'Cluster',
    primaryjoin="and_(VirtualMachinePool.cluster_id == Cluster.id, VirtualMachinePool.zone_number == Cluster.zone_number)",
    foreign_keys=[cluster_id, zone_number])

  def __init__(self, id=None, name=None, zone_number=None, cluster_id=None, cardinality=None):
    self.id = id
    self.name = name
    self.cluster_id = cluster_id
    self.zone_number = zone_number
    self.cardinality = cardinality

  def get_memberships(self):
    return PoolMembership.query.filter_by(pool=self).all()

  def get_memberships_by_vm_id(self):
    memberships = {}
    for membership in self.get_memberships():
      memberships[membership.vm_id] = membership
    return memberships

  def name_for_number(self, number):
    pattern = re.compile("^([^\.]+)\.(.*)$")
    match = pattern.match(self.name)
    if match is None:
      raise Exception("Failed to parse pool name for hostname of number: {}".format(number))
    return '{}{}.{}'.format(match.group(1), number, match.group(2))


  def get_member_vms_by_num(self):
    num_pattern = re.compile("^[^\.]+(\d+)\.")
    memberships_by_vm_id = self.get_memberships_by_vm_id()
    vms_by_num = {}
    one_proxy = OneProxy(self.cluster.zone.xmlrpc_uri, self.cluster.zone.session_string, verify_certs=False)
    for vm in one_proxy.get_vms(INCLUDING_DONE):
      if vm.id in memberships_by_vm_id:
        match = num_pattern.match(vm.name)
        if match is not None:
          vms_by_num[int(match.group(1))] = vm
    return vms_by_num


  def get_cluster(self):
    return Cluster.query.filter_by(zone_number=self.zone_number, id=self.cluster_id).first()

  @staticmethod
  def get_all(cluster):
    return db.session.query(VirtualMachinePool).filter_by(cluster=cluster)

  def get_peer_pools(self):
    return db.session.query(VirtualMachinePool).filter_by(cluster=self.cluster)


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


class PoolEditForm(Form):
  name = StringField('Name', [InputRequired()])
  cardinality = StringField('Cardinality', [InputRequired()])
  template = TextAreaField('Zone Template')
  vars = TextAreaField('Zone Variables')


class GenerateTemplateForm(Form):
  pass
