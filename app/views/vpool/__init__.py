import sys, traceback, re, io
from flask import request, redirect, url_for, render_template, flash, Blueprint, g, Markup
from flask.ext.login import current_user, login_required
from jinja2 import Environment
from datetime import datetime
from flask.ext.login import current_user
from app import app, db
from app.one import OneProxy, INCLUDING_DONE
from app.views.template.models import ObjectLoader
from app.views.vpool.models import PoolMembership, VirtualMachinePool, PoolEditForm, GenerateTemplateForm, \
  ExpandException
from app.views.common.models import ActionForm
from app.views.zone.models import Zone
from app.views.cluster.models import Cluster
from app.views.template.models import VarParser
from app.jira_api import JiraApi

vpool_bp = Blueprint('vpool_bp', __name__, template_folder='templates')

@vpool_bp.before_request
def get_current_user():
  g.user = current_user

@vpool_bp.route('/vpool/test/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def test(pool_id):
  form = ActionForm()
  jira = JiraApi()
  jira.connect()
  pool = VirtualMachinePool.query.get(pool_id)
  return render_template('vpool/test.html', pool=pool)

@vpool_bp.route('/vpool/convert/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def convert(pool_id):
  form = ActionForm()
  jira = JiraApi()
  jira.connect()
  pool = VirtualMachinePool.query.get(pool_id)
  return render_template('vpool/test.html', pool=pool)

@vpool_bp.route('/vpool/remove_done/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def remove_done(pool_id):
  form = ActionForm()
  jira = JiraApi()
  jira.connect()
  pool = one_proxy = members = None
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    members = pool.get_memberships()
  except Exception as e:
    flash("There was an error finshed VMs: {}".format(e), category='danger')
    return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  if request.method == 'POST' and form.validate():
    try:
      if request.form['action'] == 'cancel':
        flash('Cleanup of {} cancelled'.format(pool.name), category='info')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      elif request.form['action'] == 'confirm':
        vm_ids_to_delete = [int(id) for id in request.form.getlist('done_vm_ids')]
        delete_members = []
        for m in members:
          if m.vm.id in vm_ids_to_delete:
            delete_members.append(m)
        delete_ticket = jira.instance.create_issue(
          project=app.config['JIRA_PROJECT'],
          summary='[auto-{}] Pool Cleanup: {} (deleting {} done VMs)'.format(
            current_user.username, pool.name, len(vm_ids_to_delete)),
          description="Pool cleanup triggered that will delete {} VM(s): \n\n*{}".format(
            len(vm_ids_to_delete),
            "\n*".join(['ID {}: {} ({})'.format(m.vm.id, m.vm.name, m.vm.ip_address) for m in delete_members])),
          customfield_13842=jira.get_datetime_now(),
          issuetype={'name': 'Task'})
        one_proxy = OneProxy(pool.cluster.zone.xmlrpc_uri, pool.cluster.zone.session_string, verify_certs=False)
        for m in delete_members:
          one_proxy.action_vm(m.remove_cmd(), m.vm.id)
          db.session.delete(m)
        db.session.commit()
        flash('Deleted {} done VMs to cleanup pool {}'.format(len(delete_members), pool.name))
        jira.resolve(delete_ticket)
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
    except Exception as e:
      flash("Error performing cleanup of pool {}: {}".format(pool.name, e), category='danger')
      jira.defect_for_exception("Error during cleanup of pool {}".format(pool.name), e)
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/remove_done.html',
                         form=form,
                         pool=pool,
                         members=members)

@vpool_bp.route('/vpool/shrink/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def shrink(pool_id):
  pool = shrink_vm_ids = None
  form = ActionForm()
  jira = JiraApi()
  jira.connect()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    members = pool.get_memberships()
    if request.method == 'POST' and form.validate():
      shrink_vm_ids = [int(id) for id in request.form.getlist('shrink_vm_ids')]
    shrink_members = pool.get_members_to_shrink(members, shrink_vm_ids)
    if shrink_members is None or len(shrink_members) == 0:
      raise Exception("Cannot determine any members to shutdown for shrinking")
  except Exception as e:
    flash("There was an error determining memberships for shrinking: {}".format(e), category='danger')
    return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  if request.method == 'POST' and form.validate():
    try:
      if request.form['action'] == 'cancel':
        flash('Shrinking {} cancelled'.format(pool.name), category='info')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      elif request.form['action'] == 'confirm':
        vm_ids_to_shutdown = request.form.getlist('shrink_vm_ids')
        shrink_ticket = jira.instance.create_issue(
          project=app.config['JIRA_PROJECT'],
          summary='[auto-{}] Pool Shrink: {} ({} to {})'.format(
            current_user.username, pool.name, len(members), pool.cardinality),
          description="Pool shrink triggered that will shutdown {} VM(s): \n\n*{}".format(
            len(vm_ids_to_shutdown),
            "\n*".join(['ID {}: {} ({})'.format(m.vm.id, m.vm.name, m.vm.ip_address) for m in shrink_members])),
          customfield_13842=jira.get_datetime_now(),
          issuetype={'name': 'Task'})
        # jira.instance.transition_issue(shrink_ticket, '5', assignee={'name': 'ipgbdautomation'}, resolution={'id': '32'})
        one_proxy = OneProxy(pool.cluster.zone.xmlrpc_uri, pool.cluster.zone.session_string, verify_certs=False)
        for m in shrink_members:
          one_proxy.action_vm(m.remove_cmd(), m.vm.id)
          db.session.delete(m)
        db.session.commit()
        jira.resolve(shrink_ticket)
        flash('Shutdown {} VMs to shrink pool {} to cardinality of {}'.format(
          len(shrink_members), pool.name, pool.cardinality))
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
    except Exception as e:
      flash("Error shrinking pool {}: {}".format(pool.name, e), category='danger')
      jira.defect_for_exception("Error shrinking pool {}".format(pool.name), e)
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/shrink.html',
                         form=form,
                         pool=pool,
                         shrink_members=shrink_members)

@vpool_bp.route('/vpool/expand/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def expand(pool_id):
  pool = members = expansion_names = form_expansion_names = None
  form = ActionForm()
  jira = JiraApi()
  try:
    jira.connect()
    pool = VirtualMachinePool.query.get(pool_id)
    members = pool.get_memberships()
    if request.method == 'POST' and form.validate():
      form_expansion_names = request.form.getlist('expansion_names')
    expansion_names = pool.get_expansion_names(members, form_expansion_names)
  except Exception as e:
    flash("There was an error determining new names required for expansion: {}".format(e), category='danger')
    return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  if request.method == 'POST' and form.validate():
    crq = None
    try:
      if request.form['action'] == 'cancel':
        flash('Expansion of {} cancelled'.format(pool.name), category='info')
        return redirect(url_for('vpool_bp.view', pool_id=pool.id))
      elif request.form['action'] == 'confirm':
        logging = jira.instance.issue('SVC-1020')
        print("logging service obtained: {}".format(logging.key))
        start, end = jira.next_immediate_window_dates()
        flash("start={}, end={}".format(start, end))
        if True:
          crq = jira.instance.create_issue(
            project=app.config['JIRA_CRQ_PROJECT'],
            issuetype={'name': 'Change Request'},
            assignee={'name': app.config['JIRA_USERNAME']},
            summary='[auto-{}] Pool Expansion: {} ({} to {})'.format(
              current_user.username, pool.name, len(members), pool.cardinality),
            description="Pool expansion triggered that will instantiate {} new VM(s): \n\n*{}".format(
              len(expansion_names),
              "\n*".join(expansion_names)),
            customfield_14530=start,
            customfield_14531=end,
            customfield_19031={'value': 'Maintenance'},
            customfield_15152=[{'value': 'Global'}],
            customfield_19430={'value': 'No conflict with any restrictions'},
            customfield_14135={'value': 'IPG', 'child': {'value': 'IPG Big Data'}},
            customfield_17679="Pool expansion required")
          flash(Markup("CRQ Created: {}".format(JiraApi.ticket_link(crq))))
          jira.instance.transition_issue(crq, app.config['JIRA_TRANSITION_CRQ_PLANNING'])
          jira.instance.create_issue_link('Relate', crq, logging)
          task = jira.instance.create_issue(
            issuetype={'name': 'MOP Task'},
            assignee={'name': app.config['JIRA_USERNAME']},
            project=app.config['JIRA_CRQ_PROJECT'],
            summary='[auto-{}] expansion'.format(current_user.username),
            parent={'key': crq.key},
            customfield_14135={'value': 'IPG', 'child': {'value': 'IPG Big Data'}},
            customfield_15150={'value': 'No'})
          flash(Markup("Sub task created: {}".format(JiraApi.ticket_link(task))))
          jira.instance.transition_issue(task, app.config['JIRA_TRANSITION_TASK_PLANNING'])
          jira.instance.transition_issue(task, app.config['JIRA_TRANSITION_TASK_WRITTEN'])
          jira.approver_instance.transition_issue(task, app.config['JIRA_TRANSITION_TASK_APPROVED'])
          jira.instance.transition_issue(crq, app.config['JIRA_TRANSITION_CRQ_PLANNED_CHANGE'])
          env = Environment(loader=ObjectLoader())
          for hostname in expansion_names:
            vars = VarParser.parse_kv_strings_to_dict(
              pool.cluster.zone.vars,
              pool.cluster.vars,
              pool.vars,
              'hostname={}'.format(hostname))
            vm_template = env.from_string(pool.template).render(pool=pool, vars=vars)
            attachment_content = io.StringIO(vm_template)
            jira.instance.add_attachment(
              issue=task,
              filename='{}.template'.format(hostname),
              attachment=attachment_content)
          jira.approver_instance.transition_issue(crq, app.config['JIRA_TRANSITION_CRQ_APPROVE'])
          flash(Markup("Pool expansion ticket created for pool {} ticket {}".format(pool.name, JiraApi.ticket_link(crq))))
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
    except Exception as e:
      raise e
      defect_ticket = jira.defect_for_exception("Pool Expansion Ticket Failed", e)
      flash(Markup('Error expanding pool {} (defect ticket contains exception: {})'.format(
        pool.name, JiraApi.ticket_link(defect_ticket))), category='danger')
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/expand.html',
                       form=form,
                       pool=pool,
                       expansion_names=expansion_names)

@vpool_bp.route('/vpool/view/<int:pool_id>', methods=['GET', 'POST'])
@login_required
def view(pool_id):
  pool = members = None
  vms_by_id = {}
  form = ActionForm()
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    members = pool.get_memberships()
  except Exception as e:
    traceback.print_exc(file=sys.stdout)
    flash("There was an error fetching pool_id={}: {}".format(pool_id, e), category='danger')
    return redirect(url_for('cluster_bp.view', cluster_id=pool.cluster.id, zone_number=pool.cluster.zone.number))
  return render_template('vpool/view.html',
                         form=form,
                         pool=pool,
                         members=members)

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
      # raise e
      flash('There was an error deleting pool {}: {}'.format(pool.name, e), category='danger')
      return redirect(url_for('vpool_bp.view', pool_id=pool.id))
  return render_template('vpool/delete.html',
                         form=form,
                         pool=pool,
                         vms_by_id=vms_by_id)

@vpool_bp.route('/vpool/<int:pool_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(pool_id):
  form = pool = one_proxy = members = None
  try:
    pool = VirtualMachinePool.query.get(pool_id)
    form = PoolEditForm(request.form, obj=pool)
    members = pool.get_memberships()
  except Exception as e:
    flash("There was an error fetching objects required for editing pool {}: {}".format(
      pool.name, e))
    return redirect(url_for('vpool_bp.view', pool_id=pool.id))
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
                         members=members,
                         pool=pool)

@vpool_bp.route('/vpool/<int:pool_id>/generate_template', methods=['GET', 'POST'])
@login_required
def gen_template(pool_id):
  pool = VirtualMachinePool.query.get(pool_id)
  zone = Zone.query.get(pool.cluster.zone.number)
  members = pool.get_memberships()
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
        var_string)
      env = Environment(loader=ObjectLoader())
      template = env.from_string(pool.template).render(pool=pool, cluster=cluster, vars=vars)
      flash('Template Generated for {}'.format(pool.name))
    except Exception as e:
      flash("Error generating template: {}".format(e), category='danger')
  return render_template('vpool/generate_template.html',
                         pool=pool,
                         members=members,
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
    # raise e
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
