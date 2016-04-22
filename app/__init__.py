from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://lifeguard:l1f3guard@localhost/lifeguard'
app.config['WTF_CSRF_SECRET_KEY'] = 'xl7zok8EUZZo1y/UcV/u+V35TTHjMaslqQ=='
#app.config['LDAP_PROVIDER_URL'] = 'ldap://dc-g01.ad0.bblabs'
app.config['LDAP_PROVIDER_URL'] = 'dc-g01.ad0.bblabs'
app.config['LDAP_PROTOCOL_VERSION'] = 3

db = SQLAlchemy(app)

app.secret_key = 'mUl+FzdjyfSGTAag5lJQn/zGZiV8zavPFg=='

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from app.auth.views import auth
app.register_blueprint(auth)

db.create_all()

