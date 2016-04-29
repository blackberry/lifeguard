from flask import request, render_template, flash, redirect, url_for, Blueprint, g
from flask.ext.login import current_user, login_required
from app.blueprints.zone.models import Zone, ZoneForm, VmActionForm
from app import db
from app.one import OneProxy

zone_bp = Blueprint('zone_bp', __name__)


@zone_bp.before_request
def get_current_user():
  g.user = current_user


@zone_bp.route('/zone/list')
@login_required
def list():
  zones = Zone.query.order_by(Zone.id.desc()).all()
  return render_template('zones_list.html', zones=zones)


@zone_bp.route('/zone/<int:zone_id>', methods=['GET', 'POST'])
@login_required
def view(zone_id):
  zone = Zone.query.get(zone_id)
  one_proxy = OneProxy(zone.xmlrpc_uri, zone.session_string, verify_certs=False)
  vms = one_proxy.get_vms()
  form = VmActionForm()
  if form.validate_on_submit():
    flash(request.form['action'], category='info')
  return render_template('zone.html', form=form, zone=zone, vms=vms)


@zone_bp.route('/zone/edit/<int:object_id>', methods=['GET', 'POST'])
@zone_bp.route('/zone/create', methods=['GET', 'POST'], defaults={'object_id': None})
@login_required
def manage(object_id):
  zone = Zone()
  form_title = "Create New Zone"
  if object_id is not None:
    zone = Zone.query.get(object_id)
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


@zone_bp.route('/zone/delete/<int:object_id>', methods=['GET', 'POST'])
@login_required
def delete(object_id):
  zone = Zone.query.get(object_id)
  form = ConfirmDeleteForm(request.form, zone=zone)
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
