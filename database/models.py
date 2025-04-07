from database.db import db
from datetime import datetime

class Jogador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    vitorias = db.Column(db.Integer, default=0)
    saldo_a_favor = db.Column(db.Integer, default=0)
    saldo_contra = db.Column(db.Integer, default=0)
    saldo_total = db.Column(db.Integer, default=0)
    torneio_id = db.Column(db.Integer, db.ForeignKey('torneio.id'), nullable=False)

class Torneio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    finalizado = db.Column(db.Boolean, default=False)
    jogadores = db.relationship('Jogador', backref='torneio', lazy=True)

