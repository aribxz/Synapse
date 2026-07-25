from flask import Flask
from config import Config

def create_app():
    Config.validate()

    app = Flask(__name__) # Flask automatically assumes the name of the file.
    app.config.from_object(Config) # Think of it as a dictionary which contains your api keys.

    from app.routes.main import main_bp
    app.register_blueprint(main_bp) # Registers blueprint.

    return app