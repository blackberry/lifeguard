from datetime import datetime
from flask import request, render_template, flash, redirect, url_for, Blueprint, g
from flask.ext.login import current_user, login_required
from app.views.zone.models import Zone
from app.views.virtual_pools.models import  PoolMembership, VirtualMachinePool
from app.views.common.models import ActionForm
from app import app, db

from app.one import OneProxy

orphaned_vms_bp = Blueprint('orphaned_vms_bp', __name__)

@orphaned_vms_bp.before_request
def get_current_user():
  g.user = current_user


@orphaned_vms_bp.route('/orphaned_vms/zone/<int:number>', methods=['GET', 'POST'])
@login_required
def list(number):
  vms = []
  id_to_vm = {}
  selected_vm_ids = {}
  total_vm_count = 0
  zone = None
  try:
    zone = Zone.query.get(number)
    one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
    memberships = {}
    for membership in db.session.query(PoolMembership).join(
            PoolMembership.pool, aliased=True).filter_by(zone=zone):
      memberships[membership.vm_id] = membership
    for vm in one_proxy.get_vms():
      total_vm_count += 1
      if vm.id not in memberships:
        vms.append(vm)
        id_to_vm[vm.id] = vm
  except Exception as e:
    flash("Error fetching VMs in zone number {}: {}".format(number, e), category='danger')
  form = ActionForm()
  if form.validate_on_submit():
    selected_clusters = {}
    for id in request.form.getlist('chk_vm_id'):
      selected_vm_ids[int(id)] = id
      selected_clusters[id_to_vm[int(id)].disk_cluster.id] = True
    proceed = True
    if len(selected_vm_ids) == 0:
      flash("No virtual machines were selected!", category='danger')
      proceed = False
    elif len(selected_clusters.keys()) != 1:
      flash("Selected VMs must all be in the same cluster", category='danger')
      proceed = False
    if proceed and request.form['action'] == 'New Pool':
      try:
        pool = VirtualMachinePool(name=request.form['new_pool_name'],
                                  zone_number=zone.number,
                                  cluster_id=next(iter(selected_clusters.keys())))
        db.session.add(pool)
        db.session.flush()
        for vm_id in selected_vm_ids.keys():
          membership = PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow())
          db.session.add(membership)
        db.session.commit()
        flash('Successfully created new pool: {} with {} pool members'.format(
          pool.name, len(selected_vm_ids.keys())), category='success')
      except Exception as e:
        db.session.rollback()
        flash('Error creating your new pool: {}'.format(e), category='danger')
  return render_template('orphaned_vms.html',
                         form=form,
                         zone=zone,
                         vms=vms,
                         selected_vm_ids=selected_vm_ids,
                         total_vm_count=total_vm_count)