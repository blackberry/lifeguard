from flask import request, render_template, flash, redirect, url_for, Blueprint
from flask.ext.login import login_required
from app.views.zone.models import Zone, ZoneForm
from app.views.common.models import ActionForm
from app import app, db

zone_bp = Blueprint('zone_bp', __name__, template_folder='templates')

@zone_bp.route('/zone/list')
@login_required
def list():
  zones = Zone.query.order_by(Zone.number.desc()).all()
  return render_template('zones_list.html', zones=zones)


@zone_bp.route('/zone/edit/<int:number>', methods=['GET', 'POST'])
@zone_bp.route('/zone/create', methods=['GET', 'POST'], defaults={'number': None})
@login_required
def manage(number):
  zone = Zone()
  form_title = "Create New Zone"
  if number is not None:
    zone = db.session.query(Zone).filter_by(number=number).first()
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
