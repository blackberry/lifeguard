from flask import request, render_template, flash, redirect, url_for, Blueprint
from flask.ext.login import login_required
from app.views.zone.models import Zone
from app.views.cluster.models import Cluster, ClusterTemplateForm
from app import db

cluster_bp = Blueprint('cluster_bp', __name__, template_folder='templates')

@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>', methods=['GET'])
@login_required
def view(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = zone.get_cluster(cluster_id)
  return render_template('cluster/view.html', cluster=cluster)


@cluster_bp.route('/cluster/<int:zone_number>/<int:cluster_id>/template', methods=['GET', 'POST'])
@login_required
def edit_template(zone_number, cluster_id):
  zone = Zone.query.get(zone_number)
  cluster = zone.get_cluster(cluster_id)
  form = ClusterTemplateForm(request.form, obj=cluster)
  if request.method == 'POST':
    if request.form['action'] == "cancel":
      flash('Cancelled {} cluster template update'.format(cluster.name), category="info")
      return redirect(url_for('cluster_bp.view', cluster_id=cluster.id))
    elif request.form['action'] == "save":
      if form.validate():
        try:
          form.populate_obj(cluster)
          db.session.add(cluster)
          db.session.commit()
          flash('Successfully saved cluster template for {} (ID={}).'
                .format(cluster.name, cluster.id), 'success')
          return redirect(url_for('zone_bp.list'))
        except Exception as e:
          flash('Failed to save cluster template, error: {}'.format(e), 'danger')
  if form.errors:
    flash("Errors must be resolved before cluster template can be saved", 'danger')
  return render_template('cluster/edit_template.html', form=form, cluster=cluster)