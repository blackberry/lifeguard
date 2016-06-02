from flask import request, render_template, flash, redirect, url_for, Blueprint
from flask.ext.login import login_required
from app.views.cluster.models import Cluster, ClusterTemplateForm, CreateVmForm, GenerateTemplateForm
from app.views.zone.models import Zone
from app.views.vpool.models import VirtualMachinePool
from app import db
from app.one import OneProxy
from jinja2 import Environment, FunctionLoader
from app.jira_api import JiraApi
from app.views.template.models import ObjectLoader


cluster_bp = Blueprint('cluster_bp', __name__, template_folder='templates')


def zone_template_loader(zone_number):
  return Zone.query.get(zone_number).template


def object_template_loader(obj):
  return object.template


@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>', methods=['GET'])
@login_required
def view(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = Cluster.query.filter_by(zone=zone, id=cluster_id).first()
  pools = VirtualMachinePool.query.filter_by(cluster_id=cluster.id, zone_number=cluster.zone_number).all()
  return render_template('cluster/view.html', cluster=cluster, pools=pools)


@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>/template', methods=['GET', 'POST'])
@login_required
def edit_template(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = Cluster.query.filter_by(zone=zone, id=cluster_id).first()
  pools = VirtualMachinePool.query.filter_by(cluster_id=cluster.id, zone_number=cluster.zone_number).all()
  form = ClusterTemplateForm(request.form, obj=cluster)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled {} cluster template update'.format(cluster.name), category="info")
      return redirect(url_for('cluster_bp.view', zone_number=zone.number, cluster_id=cluster.id))
    elif request.form['action'] == "save":
      try:
        cluster.template = request.form['template']
        cluster.vars = request.form['vars']
        db.session.add(cluster)
        db.session.commit()
        flash('Successfully saved cluster template for {} (ID={}).'
              .format(cluster.name, cluster.id), 'success')
        return redirect(url_for('cluster_bp.view', zone_number=zone.number, cluster_id=cluster.id))
      except Exception as e:
        flash('Failed to save cluster template, error: {}'.format(e), 'danger')
  if form.errors:
    flash("Errors must be resolved before cluster template can be saved", 'danger')
  return render_template('cluster/template.html',
                         form=form,
                         cluster=cluster,
                         pools=pools)

@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>/create_vm', methods=['GET', 'POST'])
@login_required
def vm_create(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = Cluster.query.filter_by(zone=zone, id=cluster_id).first()
  pools = VirtualMachinePool.query.filter_by(cluster=cluster).all()
  vars = {'hostname': None,
          'cpu': None,
          'vcpu': None,
          'memory_megabytes': None}
  vm_template = None
  form = CreateVmForm(request.form)
  if form.validate_on_submit():
    if request.form['action'] == 'cancel':
      flash('Cancelled creating VM in {}'.format(cluster.name), category="info")
      return redirect(url_for('cluster_bp.view', zone_number=zone.number, cluster_id=cluster.id))
    try:
      for k, v in vars.items():
        if request.form[k] is None or request.form[k] == '':
          raise Exception('expected parameter {} is {}'.format(k, v))
        vars[k] = request.form[k]
      vars = cluster.parsed_vars(vars)
      one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
      obj_loader = FunctionLoader(object_template_loader)
      env = Environment(loader=obj_loader)
      vm_template = env.from_string(cluster.template).render(cluster=cluster, vars=vars)
      jira_api = JiraApi()
      jira_api.connect()
      new_issue = jira_api.instance.create_issue(
        project='IPGBD',
        summary='[auto] VM instantiated: {}'.format(vars['hostname']),
        description='Template: {}'.format(vm_template),
        customfield_13842=jira_api.get_datetime_now(),
        issuetype={'name': 'Task'})
      one_proxy.create_vm(template=vm_template)
      flash('Created VM: {}'.format(vars['hostname']))
    except Exception as e:
      raise e
      flash("Error parsing GET parameters: {}".format(e), category='danger')
  return render_template('cluster/vm_create.html',
                         form=form,
                         cluster=cluster,
                         pools=pools,
                         zone=zone,
                         vm_template=vm_template)

@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>/generate_template', methods=['GET', 'POST'])
@login_required
def gen_template(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = Cluster.query.filter_by(zone=zone, id=cluster_id).first()
  pools = VirtualMachinePool.query.filter_by(cluster=cluster).all()
  form = GenerateTemplateForm(request.form)
  vars = {}
  var_string = None
  template = None
  if request.method == 'POST':
    if request.form['action'] == 'cancel':
      flash('Cancelled template generation in {}'.format(cluster.name), category="info")
      return redirect(url_for('cluster_bp.view', zone_number=zone.number, cluster_id=cluster.id))
    try:
      var_string = request.form['vars']
      for line in var_string.split("\n"):
        k, v = line.split("=", 2)
        vars[k] = v
      vars = cluster.parsed_vars(vars)
      obj_loader = ObjectLoader()
      env = Environment(loader=obj_loader)
      template = env.from_string(cluster.template).render(cluster=cluster, vars=vars)
      flash('Template Generated for {}'.format(cluster.name))
    except Exception as e:
      raise e
      #flash("Error generating template: {}".format(e), category='danger')
  return render_template('cluster/generate_template.html',
                         cluster=cluster,
                         form=form,
                         pools=pools,
                         zone=zone,
                         var_string=var_string,
                         template=template)



