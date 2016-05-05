from flask import request, render_template, flash, redirect, url_for, Blueprint, g
from flask.ext.login import current_user, login_required
from app.blueprints.zone.models import Zone, ZoneForm, VmActionForm, PoolMembership, VirtualMachinePool
from app import db
from app.one import OneProxy

zone_bp = Blueprint('zone_bp', __name__)


@zone_bp.before_request
def get_current_user():
  g.user = current_user


@zone_bp.route('/zone/list')
@login_required
def list():
  zones = Zone.query.order_by(Zone.number.desc()).all()
  return render_template('zones_list.html', zones=zones)


@zone_bp.route('/zone/<int:number>', methods=['GET', 'POST'])
@login_required
def view(number):
  vms = []
  id_to_vm = {}
  selected_vm_ids = {}
  zone = None
  try:
    zone = Zone.query.get(number)
    one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
    for vm in one_proxy.get_vms():
      vms.append(vm)
      id_to_vm[vm.id] = vm
  except Exception as e:
    flash("Error fetching VMs in zone number {}: {}".format(number, e), category='danger')
  form = VmActionForm()
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
        db.session.commit()
        flash('Successfully created new pool: {}'.format(request.form['new_pool_name']), category='success')
      except Exception as e:
        db.session.rollback()
        flash('Error creating your new pool: {}'.format(e), category='danger')


  return render_template('zone.html',
                         form=form,
                         zone=zone,
                         vms=vms,
                         selected_vm_ids=selected_vm_ids)


@zone_bp.route('/zone/edit/<int:number>', methods=['GET', 'POST'])
@zone_bp.route('/zone/create', methods=['GET', 'POST'], defaults={'number': None})
@login_required
def manage(number):
  zone = Zone()
  form_title = "Create New Zone"
  if number is not None:
    zone = db.session.query(Zone).filter_by(number=number).first()
    form_title = 'Edit {}'.format(zone.name)
  form = ZoneForm(request.form, obj=zone)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled:  {}'.format(form_title), category="info")
      return redirect(url_for('zone_bp.list'))
    elif request.form['action'] == "save":
      if form.validate():
        try:
          form.populate_obj(zone)
          db.session.add(zone)
          db.session.commit()
          flash('Successfully saved {}.'.format(zone.name), 'success')
          return redirect(url_for('zone_bp.list'))
        except Exception as e:
          flash('Failed to save zone, error: {}'.format(e), 'danger')
          return render_template('manage_zone.html', form=form, form_title=form_title)
  if form.errors:
    flash("Errors must be resolved before zone can be saved", 'danger')
  return render_template('manage_zone.html', form_title=form_title, form=form, zone=zone)


@zone_bp.route('/zone/delete/<int:number>', methods=['GET', 'POST'])
@login_required
def delete(number):
  zone = Zone.query.get(number=number)
  form = VmActionForm(request.form, zone=zone)
  if request.method == 'POST' and form.validate():
    try:
      if request.form['action'] == 'Cancel':
        flash('Delete {} action cancelled'.format(zone.name), category='info')
        return redirect(url_for('zone_bp.list'))
      elif request.form['action'] == 'Confirm':
        db.session.delete(zone)
        db.session.commit()
        flash('{} has been deleted'.format(zone.name), category='success')
        return redirect(url_for('zone_bp.list'))
    except Exception as e:
      flash('There was an error deleting zone {}'.format(zone.name), category='success')
      return redirect(url_for('zone_bp.list'))
  return render_template('confirm_zone_delete.html', form=form, zone=zone)
