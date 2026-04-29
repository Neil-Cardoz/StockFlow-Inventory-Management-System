import logging
from flask import Flask
from models import db
from routes import products_bp

logging.basicConfig(level=logging.INFO)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.setdefault("SQLALCHEMY_DATABASE_URI", "postgresql://user:password@localhost/stockflow")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(products_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
