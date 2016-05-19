from flask import request, render_template, flash, redirect, url_for, Blueprint
from flask.ext.login import login_required
from app.views.cluster.models import Cluster, ClusterTemplateForm
from app.views.zone.models import Zone
from app.views.vpool.models import VirtualMachinePool
from app import db
from app.one import OneProxy

cluster_bp = Blueprint('cluster_bp', __name__, template_folder='templates')

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
  cluster = zone.get_cluster(cluster_id)
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
  return render_template('cluster/edit_template.html', form=form, cluster=cluster)