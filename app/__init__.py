from flask import Flask
from .models import init_db

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = '2NFAPTgd925uec5hXRK8Ls4'

    app.config['UPLOAD_FOLDER'] = 'planilhas'
    app.config['STATIC_FOLDER'] = 'app/static'

    from .routes import bp
    app.register_blueprint(bp)

    init_db(app)

    return app