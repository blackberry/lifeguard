from flask import request, redirect, url_for, render_template, flash, Blueprint, g, Markup
from flask.ext.login import current_user, login_required
from app.views.vpool.models import PoolMembership, VirtualMachinePool, CreateVmForm
from app.views.common.models import ActionForm
from app.views.zone.models import Zone
from app.views.cluster.models import Cluster
from app import db
from app.one import OneProxy
from jinja2 import Environment, FunctionLoader
from app.jira_api import JiraApi
from datetime import datetime

vpool_bp = Blueprint('vpool_bp', __name__, template_folder='templates')


@vpool_bp.before_request
def get_current_user():
  g.user = current_user


def zone_template_loader(zone_number):
  return Zone.query.get(zone_number).template


@vpool_bp.route('/test_vm_create/zone/<int:number>', methods=['GET', 'POST'])
@login_required
def vm_create(number):
  zone = Zone.query.get(number)
  vars = {'hostname': None,
          'cpu': None,
          'vcpu': None,
          'memory_megabytes': None}
  vm_template = None
  form = CreateVmForm(request.form)
  if form.validate_on_submit():
    if request.form['action'] == 'cancel':
      redirect(url_for('zone_bp.list'))
    try:
      for k, v in vars.items():
        if request.form[k] is None or request.form[k] == '':
          raise Exception('expected parameter {} is {}'.format(k, v))
        vars[k] = request.form[k]
      vars = zone.parsed_vars(vars)
      one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
      cluster = Cluster.query.filter_by(zone=zone, id=101).first()
      obj_loader = FunctionLoader(zone_template_loader)
      env = Environment(loader=obj_loader)
      vm_template = env.from_string(cluster.template).render(cluster=cluster, vars=vars)
      #jira_api = JiraApi()
      #jira_api.connect()
      #new_issue = jira_api.instance.create_issue(
      #  project='IPGBD',
      #  summary='[auto] VM instantiated: {}'.format(vars['hostname']),
      #  description='Template: {}'.format(vm_template),
      #  customfield_13842=jira_api.get_datetime_now(),
      #  issuetype={'name': 'Task'})
      #one_proxy.create_vm(template=vm_template)
      flash('Created VM: {}'.format(vars['hostname']))
    except Exception as e:
      raise e
      flash("Error parsing GET parameters: {}".format(e), category='danger')
  return render_template('vm_create.html',
                         form=form,
                         zone=zone,
                         vm_template=vm_template)


@vpool_bp.route('/vpool/test/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def test(pool_id):
  pool = VirtualMachinePool.query.get(pool_id)
  return render_template('vpool/test.html', pool=pool)


@vpool_bp.route('/vpool/view/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def view_pool(pool_id):
  pool = None
  vms_by_id = {}
  form = ActionForm()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    #cluster = pool.get_cluster()
    one_proxy = OneProxy(pool.cluster.zone.xmlrpc_uri, pool.cluster.zone.session_string, verify_certs=False)
    vms = one_proxy.get_vms(include_done=True)
    if vms is None or len(vms) == 0:
      raise Exception("Warning: There were no VMs found in Zone!")
    for vm in vms:
      vms_by_id[vm.id] = vm
  except Exception as e:
    flash("There was an error fetching pool_id={}: {}".format(pool_id, e), category='danger')

  return render_template('vpool/view.html',
                         form=form,
                         pool=pool,
                         vms_by_id=vms_by_id)


@vpool_bp.route('/assign_to_pool/zone/<int:zone_number>/cluster/<int:cluster_id>', methods=['GET', 'POST'])
@login_required
def assign_to_pool(zone_number, cluster_id):
  # Gather the collections and objects we'll need for managing orphaned VMs
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

    #for membership in PoolMembership.query.join(VirtualMachinePool).join(Cluster).all():
    #  memberships[membership.vm_id] = membership


    for vm in one_proxy.get_vms():
      if vm.disk_cluster.id == cluster.id:
        vms.append(vm)
        id_to_vm[vm.id] = vm
    pools = VirtualMachinePool.get_all(cluster)
  except Exception as e:
    raise e
    flash("Error fetching VMs in zone number {}: {}"
          .format(zone_, e), category='danger')
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
        flash('Added {} VMs to {}'.format(len(selected_vm_ids), pool.name))
        return redirect(url_for('vpool_bp.assign_to_pool', zone_number=zone.number, cluster_id=cluster.id))
    if proceed and request.form['action'] == 'create new pool':
      try:
        if request.form['new_pool_name'] is None or request.form['new_pool_name'] == '':
          raise Exception('Pool name cannot be blank')
        pool = VirtualMachinePool(
          name=request.form['new_pool_name'],
          cluster_id=cluster.id,
          zone_number=zone.number)
        db.session.add(pool)
        db.session.flush()
        for vm_id in selected_vm_ids.keys():
          membership = PoolMembership(pool=pool, vm_id=vm_id, date_added=datetime.utcnow())
          memberships[vm_id] = membership
          db.session.add(membership)
        db.session.flush()
        db.session.commit()
        flash(Markup('Successfully created <a href="{}">{}</a> with {} pool members'.format(
          url_for('vpool_bp.view_pool', pool_id=pool.id),
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