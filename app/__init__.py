from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask(__name__)
app.config.from_envvar('LIFEGUARD_CFG_FILE')
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from app.views.auth import auth_bp
app.register_blueprint(auth_bp)

from app.views.zone import zone_bp
app.register_blueprint(zone_bp)

from app.views.cluster import cluster_bp
app.register_blueprint(cluster_bp)

from app.views.vpool import vpool_bp
app.register_blueprint(vpool_bp)

db.create_all()