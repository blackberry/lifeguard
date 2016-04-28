from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask(__name__)
app.config.from_envvar('LIFEGUARD_CFG_FILE')

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from app.blueprints.auth.views import auth
from app.blueprints.zone.views import zone_bp
#from app.blueprints.vm.views import vm_bp

app.register_blueprint(zone_bp)
app.register_blueprint(auth)
#app.register_blueprint(vm_bp)

db.create_all()