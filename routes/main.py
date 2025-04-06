from flask import Blueprint, render_template, session
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.context_processor
def inject_timestamp():
    return {'timestamp': datetime.now().timestamp()}

@bp.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@bp.route('/')
def index():
    
    # Garante estrutura completa para todos os jogadores
    for jogador in session.get('jogadores', {}).values():
        jogador.setdefault('vitorias', 0)
        jogador.setdefault('saldo_a_favor', 0)
        jogador.setdefault('saldo_contra', 0)
        jogador.setdefault('saldo_total', jogador.get('saldo_a_favor', 0) - jogador.get('saldo_contra', 0))    
        return render_template('index.html',
            grupos=session.get('grupos', []),
            confrontos=session.get('confrontos', []),
            valores_salvos=session.get('valores_salvos', {}),
            modo_torneio=session.get('modo_torneio', '28j'))