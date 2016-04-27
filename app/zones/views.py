from flask import request, render_template, flash, redirect, url_for, Blueprint, g
from flask.ext.login import current_user, login_required
from app.zones.models import Zone, ZoneForm, ConfirmForm
from app import app, db

zones = Blueprint('zones', __name__)

@zones.before_request
def get_current_user():
  g.user = current_user


@zones.route('/zones')
@login_required
def list():
  zones = Zone.query.order_by(Zone.id.desc()).all()
  return render_template('zones.html', zones=zones)


@zones.route('/zones/create', methods=['GET', 'POST'])
@login_required
def create():
  form = ZoneForm(request.form)
  if request.method == 'POST' and form.validate():
    try:
      zone = Zone(name=request.form.get('name'),
                  xmlrpc_uri=request.form.get('xmlrpc_uri'),
                  session_string=request.form.get('session_string'),
                  zone_num=request.form.get('zone_num'))
      db.session.add(zone)
      db.session.commit()
      flash('Created new zone, {}.'.format(zone.name), 'success')
      return redirect(url_for('zone.list'))
    except Exception as e:
      flash('Failed to create new zone record: {}'.format(e), 'danger')
      return render_template('create_zone.html', form=form)

  if form.errors:
    flash(form.errors, 'danger')

  return render_template('create_zone.html', form=form)

@zones.route('/zones/delete/<int:object_id>', methods=['GET', 'POST'])
@login_required
def delete(object_id):
    form = ConfirmForm(request.form)