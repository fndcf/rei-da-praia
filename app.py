from flask import Flask, session
from config import Config
from routes.main import bp as main_bp
from routes.groups import bp as groups_bp
from routes.playoffs import bp as playoffs_bp
from flask_sqlalchemy import SQLAlchemy
from database.db import db
from sqlalchemy import text

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        # Comentado para preservar os dados entre reinicializações
        # db.session.execute(text('DROP SCHEMA public CASCADE'))
        # db.session.execute(text('CREATE SCHEMA public'))
        # db.session.commit()
        
        # Apenas cria tabelas que não existem ainda
        db.create_all()

    # --------------------------------------
    # Registro de Blueprints
    # --------------------------------------
    app.register_blueprint(main_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(playoffs_bp)

    # --------------------------------------
    # Configurações de Sessão
    # --------------------------------------
    @app.before_request
    def init_session():
        """Garante estruturas básicas na sessão"""
        session.setdefault('jogadores', {})
        session.setdefault('grupos', [])
        session.setdefault('confrontos', [])
        session.setdefault('modo_torneio', '28j')

    return app

# Cria a aplicação
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)