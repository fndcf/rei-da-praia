"""Models do Banco de Dados"""
from datetime import datetime
from database.db import db

class JogadorPermanente(db.Model):
    """Novo modelo para jogadores permanentes"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)  # Nome único
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    participacoes = db.relationship('ParticipacaoTorneio', backref='jogador_permanente', lazy=True)
    
    def __repr__(self):
        return f"<JogadorPermanente {self.nome}>"


class ParticipacaoTorneio(db.Model):
    """Modelo para participação em torneios (substitui funcionalidade do Jogador)"""
    id = db.Column(db.Integer, primary_key=True)
    jogador_permanente_id = db.Column(db.Integer, db.ForeignKey('jogador_permanente.id'), nullable=False)
    torneio_id = db.Column(db.Integer, db.ForeignKey('torneio.id'), nullable=False)
    
    # Dados de desempenho no torneio
    vitorias = db.Column(db.Integer, default=0)
    saldo_a_favor = db.Column(db.Integer, default=0)
    saldo_contra = db.Column(db.Integer, default=0)
    saldo_total = db.Column(db.Integer, default=0)
    posicao_grupo = db.Column(db.Integer, default=0)
    grupo_idx = db.Column(db.Integer, default=0)
    pontuacao = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<ParticipacaoTorneio {self.id}>"


class Jogador(db.Model):
    """Mantemos o modelo Jogador para compatibilidade com código existente"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    vitorias = db.Column(db.Integer, default=0)
    saldo_a_favor = db.Column(db.Integer, default=0)
    saldo_contra = db.Column(db.Integer, default=0)
    saldo_total = db.Column(db.Integer, default=0)
    posicao_grupo = db.Column(db.Integer, default=0)
    grupo_idx = db.Column(db.Integer, default=0)
    pontuacao = db.Column(db.Integer, default=0)
    torneio_id = db.Column(db.Integer, db.ForeignKey('torneio.id'), nullable=False)
    
    # Novo campo para rastrear relação com jogador permanente
    jogador_permanente_id = db.Column(db.Integer, db.ForeignKey('jogador_permanente.id'), nullable=True)
    jogador_permanente = db.relationship('JogadorPermanente', backref='jogadores_legados')

    # NOVO: Campo para salvar a classificação geral (ordem do sorteio)
    classificacao_geral = db.Column(db.Integer, default=0)

class Torneio(db.Model):
    """Modelo para torneios"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    finalizado = db.Column(db.Boolean, default=False)
    formato_eliminatoria = db.Column(db.String(20), default='separados')  # 'separados' ou 'mistos'
    jogadores = db.relationship('Jogador', backref='torneio', lazy=True)
    participacoes = db.relationship('ParticipacaoTorneio', backref='torneio', lazy=True)

class Confronto(db.Model):
    """Modelo para confrontos"""
    id = db.Column(db.Integer, primary_key=True)

    # Relacionamentos
    torneio_id = db.Column(db.Integer, db.ForeignKey('torneio.id'), nullable=False)
    torneio = db.relationship('Torneio', backref=db.backref('confrontos', lazy=True))

    # Dados do confronto
    grupo_idx = db.Column(db.Integer, nullable=False)  # Índice do grupo
    confronto_idx = db.Column(db.Integer, nullable=False)  # Índice do confronto no grupo

    # Jogadores da dupla A
    jogador_a1_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_a1 = db.relationship('Jogador', foreign_keys=[jogador_a1_id])

    jogador_a2_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_a2 = db.relationship('Jogador', foreign_keys=[jogador_a2_id])
    
    # Jogadores da dupla B
    jogador_b1_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_b1 = db.relationship('Jogador', foreign_keys=[jogador_b1_id])
    
    jogador_b2_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_b2 = db.relationship('Jogador', foreign_keys=[jogador_b2_id])
    
    # Resultados
    pontos_dupla_a = db.Column(db.Integer, nullable=True)  # Pontos da dupla A
    pontos_dupla_b = db.Column(db.Integer, nullable=True)  # Pontos da dupla B
    
    # Metadados
    criado_em = db.Column(db.DateTime, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Confronto {self.id}: G{self.grupo_idx+1}-C{self.confronto_idx+1}>"

class ConfrontoEliminatoria(db.Model):
    """Modelo para participação em torneios (substitui funcionalidade do Jogador)"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamentos
    torneio_id = db.Column(db.Integer, db.ForeignKey('torneio.id'), nullable=False)
    torneio = db.relationship('Torneio', backref=db.backref('confrontos_eliminatorias', lazy=True))
    
    # Tipo de fase
    fase = db.Column(db.String(20), nullable=False)  # 'quartas', 'semi', 'final'
    jogo_numero = db.Column(db.Integer, nullable=False)  # Número do jogo na fase
    
    # Jogadores da dupla A
    jogador_a1_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_a1 = db.relationship('Jogador', foreign_keys=[jogador_a1_id])
    
    jogador_a2_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_a2 = db.relationship('Jogador', foreign_keys=[jogador_a2_id])
    
    # Jogadores da dupla B
    jogador_b1_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_b1 = db.relationship('Jogador', foreign_keys=[jogador_b1_id])
    
    jogador_b2_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    jogador_b2 = db.relationship('Jogador', foreign_keys=[jogador_b2_id])
    
    # Resultados
    pontos_dupla_a = db.Column(db.Integer, nullable=True)  # Pontos da dupla A
    pontos_dupla_b = db.Column(db.Integer, nullable=True)  # Pontos da dupla B
    
    # Metadados
    criado_em = db.Column(db.DateTime, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<ConfrontoEliminatoria {self.id}: {self.fase.capitalize()} - Jogo {self.jogo_numero}>" 