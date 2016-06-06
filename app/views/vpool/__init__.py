import sys, traceback
from flask import request, redirect, url_for, render_template, flash, Blueprint, g, Markup
from flask.ext.login import current_user, login_required
from jinja2 import Environment
from app import db
from app.one import OneProxy, INCLUDING_DONE
from app.views.template.models import ObjectLoader
from app.views.vpool.models import PoolMembership, VirtualMachinePool, PoolEditForm, GenerateTemplateForm
from app.views.common.models import ActionForm
from app.views.zone.models import Zone
from app.views.cluster.models import Cluster
from app.views.template.models import VarParser
from datetime import datetime
import timeit
import re


vpool_bp = Blueprint('vpool_bp', __name__, template_folder='templates')

@vpool_bp.before_request
def get_current_user():
  g.user = current_user


@vpool_bp.route('/vpool/test/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def test(pool_id):
  pool = VirtualMachinePool.query.get(pool_id)
  return render_template('vpool/test.html', pool=pool)


@vpool_bp.route('/vpool/expand/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def expand(pool_id):
  pool = None
  members = None
  member_vms_by_num = {}
  form = ActionForm()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    members = pool.get_memberships()

    start_time = timeit.default_timer()
  except Exception as e:
    flash("There was an error fetching pool_id={}: {}".format(pool_id, e), category='danger')
  if (len(members) == pool.cardinality):
    flash("Cannot expand {} ({}/{} members already exist)".format(pool.name, len(members), pool.cardinality))
    return redirect(url_for('vpool.view', pool_id=pool.id))
  if (len(members) > pool.cardinality):
    flash("Cannot expand {} ({}/{} members, need to shrink)".format(pool.name, len(members), pool.cardinality))
    return redirect(url_for('vpool.view', pool_id=pool.id))


  member_vms_by_num = pool.get_member_vms_by_num()

  for k, v in member_vms_by_num.items():
    print("member: {} = {}".format(k, v.name))


  new_names_by_num = {}
  for number in range(1, pool.cardinality + 1):
    if number not in member_vms_by_num:
      new_name = pool.name_for_number(number)
      new_names_by_num[int(number)] = new_name
      print("number: {} not in member_vms_by_num, adding value: {}".format(number, new_name))

  needed = pool.cardinality - len(member_vms_by_num)

  if len(new_names_by_num) != needed:
    for k, v in new_names_by_num.items():
      print(k, v)
    raise Exception("Error: needed {} new VMs but could only infer {} misssing names".format(needed, len(new_names_by_num)))

  numbers = {}

  for number in range(1, pool.cardinality + 1):
    if number in new_names_by_num and number in member_vms_by_num:
      raise Exception("VM number {} found in members and new names".format(number))
    if number not in new_names_by_num and number not in member_vms_by_num:
      raise Exception("VM number {} not found in members or new names".format(number))
    numbers[number] = number


  if request.method == 'POST' and form.validate():
    try:
      if request.form['action'] == 'cancel':
        flash('Delete {} action cancelled'.format(pool.name), category='info')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      elif request.form['action'] == 'confirm':
        redirect_url = url_for('cluster_bp.view', zone_number=pool.cluster.zone.number, cluster_id=pool.cluster.id)
        members = pool.get_memberships()
        for member in members:
          db.session.delete(member)
        db.session.delete(pool)
        db.session.commit()
        flash('Deleted pool {} with {} memberse'.format(pool.name, len(members)), category='success')
        return redirect(url_for('cluster_bp.view', zone_number=pool.cluster.zone.number, cluster_id=pool.cluster.id))
    except Exception as e:
      #raise e
      flash('There was an error deleting pool {}: {}'.format(pool.name, e), category='danger')
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/expand.html',
                         form=form,
                         pool=pool,
                         numbers=numbers,
                         member_vms_by_num=member_vms_by_num,
                         new_names_by_num=new_names_by_num)


@vpool_bp.route('/vpool/view/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def view(pool_id):
  pool = None
  vms_by_id = {}
  form = ActionForm()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    one_proxy = OneProxy(pool.cluster.zone.xmlrpc_uri, pool.cluster.zone.session_string, verify_certs=False)
    start_time = timeit.default_timer()
    for vm in one_proxy.get_vms(INCLUDING_DONE):
      if vm.disk_cluster is not None and vm.disk_cluster.id == pool.cluster.id:
        vms_by_id[vm.id] = vm
    flash('fetched {} vms in {} seconds'.format(len(vms_by_id), timeit.default_timer() - start_time))
  except Exception as e:
    traceback.print_exc(file=sys.stdout)
    flash("There was an error fetching pool_id={}: {}".format(pool_id, e), category='danger')
  return render_template('vpool/view.html',
                         form=form,
                         pool=pool,
                         vms_by_id=vms_by_id)


@vpool_bp.route('/vpool/delete/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def delete(pool_id):
  pool = None
  vms_by_id = {}
  form = ActionForm()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
  except Exception as e:
    flash("There was an error fetching pool_id={}: {}".format(pool_id, e), category='danger')
  if request.method == 'POST' and form.validate():
    try:
      if request.form['action'] == 'cancel':
        flash('Delete {} action cancelled'.format(pool.name), category='info')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      elif request.form['action'] == 'confirm':
        redirect_url = url_for('cluster_bp.view', zone_number=pool.cluster.zone.number, cluster_id=pool.cluster.id)
        members = pool.get_memberships()
        for member in members:
          db.session.delete(member)
        db.session.delete(pool)
        db.session.commit()
        flash('Deleted pool {} with {} memberse'.format(pool.name, len(members)), category='success')
        return redirect(url_for('cluster_bp.view', zone_number=pool.cluster.zone.number, cluster_id=pool.cluster.id))
    except Exception as e:
      #raise e
      flash('There was an error deleting pool {}: {}'.format(pool.name, e), category='danger')
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/delete.html',
                         form=form,
                         pool=pool,
                         vms_by_id=vms_by_id)


@vpool_bp.route('/vpool/<int:pool_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(pool_id):
  pool = VirtualMachinePool.query.get(pool_id)
  form = PoolEditForm(request.form, obj=pool)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled {} pool template update'.format(pool.name), category="info")
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
    elif request.form['action'] == "save":
      try:
        cardinality_pattern = re.compile("\d+")
        pool.name = request.form['name']
        pool.template = request.form['template']
        pool.vars = request.form['vars']
        if not cardinality_pattern.fullmatch(request.form['cardinality']):
          raise Exception("Cardinality {} not numeric".format(request.form['cardinality']))
        pool.cardinality = request.form['cardinality']
        db.session.add(pool)
        db.session.commit()
        flash('Successfully saved pool template for {} (ID={}).'
              .format(pool.name, pool.id), 'success')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      except Exception as e:
        flash('Failed to save pool template, error: {}'.format(e), 'danger')
  if form.errors:
    flash("Errors must be resolved before pool template can be saved", 'danger')
  return render_template('vpool/edit.html',
                         form=form,
                         pool=pool)


@vpool_bp.route('/vpool/<int:pool_id>/generate_template', methods=['GET', 'POST'])
@login_required
def gen_template(pool_id):
  pool = VirtualMachinePool.query.get(pool_id)
  zone = Zone.query.get(pool.cluster.zone.number)
  cluster = Cluster.query.filter_by(zone=zone, id=pool.cluster.id).first()
  form = GenerateTemplateForm(request.form)
  vars = {}
  var_string = None
  template = None
  if request.method == 'POST':
    if request.form['action'] == 'cancel':
      flash('Cancelled template generation for pool {}'.format(pool.name), category="info")
      return redirect(url_for('vpool_bp.view', pool_id=pool_id))
    try:
      var_string = request.form['vars']
      print('var_string: {}'.format(var_string))
      vars = VarParser.parse_kv_strings_to_dict(
        zone.vars,
        cluster.vars,
        pool.vars,
        var_string
      )
      print('in view the vars are: {}'.format(vars))
      env = Environment(loader=ObjectLoader())
      template = env.from_string(pool.template).render(pool=pool, cluster=cluster, vars=vars)
      flash('Template Generated for {}'.format(pool.name))
    except Exception as e:
      #raise e
      flash("Error generating template: {}".format(e), category='danger')
  return render_template('vpool/generate_template.html',
                         pool=pool,
                         cluster=cluster,
                         form=form,
                         zone=zone,
                         var_string=var_string,
                         template=template)


@vpool_bp.route('/assign_to_pool/zone/<int:zone_number>/cluster/<int:cluster_id>', methods=['GET', 'POST'])
@login_required
def assign_to_pool(zone_number, cluster_id):
  vms = []
  id_to_vm = {}
  selected_vm_ids = {}
  pools = None
  zone = None
  cluster = None
  memberships = {}
  try:
    zone = Zone.query.get(zone_number)
    cluster = Cluster.query.filter_by(zone=zone, id=cluster_id).first()
    one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
    for membership in PoolMembership.query.join(VirtualMachinePool).filter_by(cluster=cluster).all():
      memberships[membership.vm_id] = membership
    for vm in one_proxy.get_vms():
      if vm.disk_cluster.id == cluster.id:
        vms.append(vm)
        id_to_vm[vm.id] = vm
    pools = VirtualMachinePool.get_all(cluster)
  except Exception as e:
    #raise e
    flash("Error fetching VMs in zone number {}: {}"
          .format(zone.number, e), category='danger')
  form = ActionForm()
  active_tab = 'create_new_pool'
  # Form submission handling begins
  if form.validate_on_submit():
    # Determine which tab needs to be active based on the action
    if request.form['action'] is not None:
      print('something')
      active_tab = {
        'create new pool': 'create_new_pool',
        'add to pool': 'add_to_existing_pool'}[request.form['action']]
    # Get a list of clusters of all selected VMs--pools cannot span clusters
    selected_clusters = {}
    for id in request.form.getlist('chk_vm_id'):
      selected_vm_ids[int(id)] = id
      selected_clusters[id_to_vm[int(id)].disk_cluster.id] = True
    # Error checking begins
    proceed = True
    if len(selected_vm_ids) == 0:
      flash("No virtual machines were selected!", category='danger')
      proceed = False
    elif len(selected_clusters) != 1:
      flash("Selected VMs must all be in the same cluster", category='danger')
      proceed = False
    # Handle the appropriate action if able to proceed
    if proceed and request.form['action'] == 'add to pool':
      if (request.form['pool_id']) is None or request.form['pool_id'] == '':
        flash('No pool selected', category='danger')
      else:
        pool = VirtualMachinePool.query.get(request.form['pool_id'])
        for vm_id in selected_vm_ids.keys():
          db.session.add(PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow()))
          db.session.commit()
        flash(Markup('Successfully added {} members to pool <a href="{}">{}</a>'.format(
          len(selected_vm_ids),
          url_for('vpool_bp.view', pool_id=pool.id),
          pool.name, )), category='success')
        return redirect(url_for('vpool_bp.assign_to_pool', zone_number=zone.number, cluster_id=cluster.id))
    if proceed and request.form['action'] == 'create new pool':
      try:
        if request.form['new_pool_name'] is None or request.form['new_pool_name'] == '':
          raise Exception('Pool name cannot be blank')
        pool = VirtualMachinePool(
          name=request.form['new_pool_name'],
          cluster_id=cluster.id,
          zone_number=zone.number,
          cardinality=len(selected_vm_ids))
        db.session.add(pool)
        db.session.flush()
        for vm_id in selected_vm_ids.keys():
          membership = PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow())
          memberships[vm_id] = membership
          db.session.add(membership)
        db.session.flush()
        db.session.commit()
        flash(Markup('Successfully created <a href="{}">{}</a> with {} pool members'.format(
          url_for('vpool_bp.view', pool_id=pool.id),
          pool.name, len(selected_vm_ids))), category='success')
      except Exception as e:
        db.session.rollback()
        flash('Error creating your new pool: {}'.format(e), category='danger')
  return render_template(
    'vpool/assign_to_pool.html',
    form=form,
    zone=zone,
    cluster=cluster,
    vms=vms,
    memberships=memberships,
    selected_vm_ids=selected_vm_ids,
    pools=pools,
    active_tab_name=active_tab
  )