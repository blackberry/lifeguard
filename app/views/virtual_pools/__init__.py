from datetime import datetime
from flask import request, redirect, url_for, render_template, flash, Blueprint, g
from flask.ext.login import current_user, login_required
from app.views.virtual_pools.models import PoolMembership, VirtualMachinePool
from app.views.common.models import ActionForm
from app.views.zone.models import Zone
from app import db
from app.one import OneProxy

vpool_bp = Blueprint('vpool_bp', __name__, template_folder='templates')


@vpool_bp.before_request
def get_current_user():
  g.user = current_user


@vpool_bp.route('/virtual_pools/list/zone/<int:number>', methods=['GET', 'POST'])
@login_required
def list(number):
  zone = None
  clusters = {}
  memberships = {}
  pools = []
  try:
    zone = Zone.query.get(number)
    one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
    for cluster in one_proxy.get_clusters():
      clusters[cluster.id] = cluster
    pools = VirtualMachinePool.get_all(zone)
    for membership in PoolMembership.get_all(zone):
      memberships[membership.vm_id] = membership
  except Exception as e:
    flash("Error virtual pools in zone number {}: {}"
          .format(number, e), category='danger')
  return render_template(
    'virtual_pool_list.html',
    zone=zone,
    pools=pools,
    clusters=clusters,
    memberships=memberships)


@vpool_bp.route('/orphaned_vms/zone/<int:number>', methods=['GET', 'POST'])
@login_required
def list_orphans(number):
  vms = []
  id_to_vm = {}
  selected_vm_ids = {}
  pools = None
  zone = None
  memberships = {}
  try:
    zone = Zone.query.get(number)
    one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
    for membership in PoolMembership.get_all(zone):
      memberships[membership.vm_id] = membership
    for vm in one_proxy.get_vms():
      vms.append(vm)
      id_to_vm[vm.id] = vm
    pools = VirtualMachinePool.get_all(zone)
  except Exception as e:
    flash("Error fetching VMs in zone number {}: {}"
          .format(number, e), category='danger')
  form = ActionForm()
  active_tab = 'create_new_pool'

  if form.validate_on_submit():
    if request.form['action'] is not None:
      print('something')
      active_tab = {
        'create_new_pool': 'create_new_pool',
        'add to pool': 'add_to_existing_pool'}[request.form['action']]
    selected_clusters = {}
    for id in request.form.getlist('chk_vm_id'):
      selected_vm_ids[int(id)] = id
      selected_clusters[id_to_vm[int(id)].disk_cluster.id] = True
    proceed = True
    if len(selected_vm_ids) == 0:
      flash("No virtual machines were selected!", category='danger')
      proceed = False
    elif len(selected_clusters) != 1:
      flash("Selected VMs must all be in the same cluster", category='danger')
      proceed = False
    if proceed and request.form['action'] == 'add to pool':
      if (request.form['pool_id']) is None or request.form['pool_id'] == '':
        flash('No pool selected', category='danger')
      else:
        pool = VirtualMachinePool.query.get(request.form['pool_id'])
        for vm_id in selected_vm_ids.keys():
          db.session.add(PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow()))
          db.session.commit()
        flash('Added {} VMs to {}'.format(len(selected_vm_ids), pool.name))
        return redirect(url_for('vpool_bp.list_orphans', number=zone.number))
    if proceed and request.form['action'] == 'New Pool':
      try:
        pool = VirtualMachinePool(
          name=request.form['new_pool_name'],
          zone=zone,
          cluster_id=next(iter(selected_clusters.keys())))
        db.session.add(pool)
        db.session.flush()
        for vm_id in selected_vm_ids.keys():
          membership = PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow())
          db.session.add(membership)
        db.session.commit()
        flash('Successfully created new pool: {} with {} pool members'.format(
          pool.name, len(selected_vm_ids)), category='success')
      except Exception as e:
        db.session.rollback()
        flash('Error creating your new pool: {}'.format(e), category='danger')
  return render_template(
    'orphaned_vms.html',
    form=form,
    zone=zone,
    vms=vms,
    memberships=memberships,
    selected_vm_ids=selected_vm_ids,
    pools=pools,
    active_tab_name=active_tab
  )