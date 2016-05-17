from app.views.cluster.models import Cluster
from flask import request, render_template, flash, redirect, url_for, Blueprint
from flask.ext.login import login_required
from app.views.zone.models import Zone, ZoneForm, ZoneTemplateForm, ZoneVarsForm, Cluster
from app.views.common.models import ActionForm
from app import app, db
from app.one import OneProxy

zone_bp = Blueprint('zone_bp', __name__, template_folder='templates')

@zone_bp.route('/zone/list')
@login_required
def list():
  zones = Zone.query.order_by(Zone.number.desc()).all()
  return render_template('zone/list.html', zones=zones)

@zone_bp.route('/zone/<int:zone_number>', methods=['GET'])
@login_required
def view(zone_number):
  zone = Zone.query.get(zone_number)
  return render_template('zone/view.html', zone=zone)


@zone_bp.route('/zone/edit/<int:number>', methods=['GET', 'POST'])
@zone_bp.route('/zone/create', methods=['GET', 'POST'], defaults={'number': None})
@login_required
def manage(number):
  zone = Zone()
  form_title = "Create New Zone"
  if number is not None:
    zone = Zone.query.get(number)
    form_title = 'Edit Zone: {}'.format(zone.name)
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


@zone_bp.route('/zone/discover/<int:number>', methods=['GET', 'POST'])
@login_required
def discover(number):
  zone = Zone.query.get(number)
  one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
  one_clusters = one_proxy.get_clusters()
  for one_cluster in one_clusters:
    existing_cluster = Cluster.query.filter_by(zone_number=zone.number, id=one_cluster.id).first()
    if existing_cluster is None:
      discovered_cluster = Cluster(id=one_cluster.id, zone=zone, name=one_cluster.name)
      db.session.add(discovered_cluster)
      db.session.commit()
      flash('Newly discovered ONE cluster: {} (ID={}) in zone {}'
            .format(one_cluster.id, one_cluster.name, zone.name), category='success')
    else:
      flash('Previously discovered: {} (ID={}) in zone {}'
            .format(one_cluster.id, one_cluster.name, zone.name))
  return render_template('zone_discover.html', zone=zone, one_clusters=one_clusters)


@zone_bp.route('/zone/template/<int:number>', methods=['GET', 'POST'])
@login_required
def edit_template(number):
  zone = Zone.query.get(number)
  form = ZoneTemplateForm(request.form, obj=zone)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled {} template update'.format(zone.name), category="info")
      return redirect(url_for('zone_bp.list'))
    elif request.form['action'] == "save":
      if form.validate():
        try:
          form.populate_obj(zone)
          db.session.add(zone)
          db.session.commit()
          flash('Successfully saved template for {}.'.format(zone.name), 'success')
          return redirect(url_for('zone_bp.list'))
        except Exception as e:
          flash('Failed to save zone template, error: {}'.format(e), 'danger')
  if form.errors:
    flash("Errors must be resolved before zone template can be saved", 'danger')
  return render_template('zone_edit_template.html', form=form, zone=zone)


@zone_bp.route('/zone/variables/<int:number>', methods=['GET', 'POST'])
@login_required
def edit_vars(number):
  zone = Zone.query.get(number)
  form = ZoneVarsForm(request.form, obj=zone)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled {} template update'.format(zone.name), category="info")
      return redirect(url_for('zone_bp.list'))
    elif request.form['action'] == "save":
      if form.validate():
        try:
          form.populate_obj(zone)
          db.session.add(zone)
          db.session.commit()
          flash('Successfully saved template variables for {}.'.format(zone.name), 'success')
          return redirect(url_for('zone_bp.list'))
        except Exception as e:
          flash('Failed to save zone template variables, error: {}'.format(e), 'danger')
  if form.errors:
    flash("Errors must be resolved before zone variables can be saved", 'danger')
  return render_template('zone_edit_vars.html', form=form, zone=zone)


@zone_bp.route('/zone/delete/<int:number>', methods=['GET', 'POST'])
@login_required
def delete(number):
  zone = Zone.query.get(number)
  form = ActionForm(request.form, zone=zone)
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
