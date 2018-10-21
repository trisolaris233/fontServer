from flask_script import Manager
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    return app

application = create_app()

if __name__ == "__main__":
    application.run()