# __init__.py file is a package.
from flask import Flask 

def create_app():
    app = Flask(__name__)

    from app.routes.main import main_bp  #Tells to look inside app, then routes for main file
    app.register_blueprint(main_bp)

    return app