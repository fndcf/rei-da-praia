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
    # Inicializa valores_salvos se não existir
    session.setdefault('valores_salvos', {})
    
    # Configurações padrão para cada modo
    modos_validos = ['20j', '24j', '28j', '32j']
    modo_atual = session.get('modo_torneio', '28j')
    
    # Garante que o modo atual é válido
    if modo_atual not in modos_validos:
        modo_atual = '28j'
        session['modo_torneio'] = modo_atual
    
    # Atualiza estrutura dos jogadores
    if 'jogadores' in session:
        for jogador in session['jogadores'].values():
            jogador.setdefault('vitorias', 0)
            jogador.setdefault('saldo_a_favor', 0)
            jogador.setdefault('saldo_contra', 0)
            jogador['saldo_total'] = jogador['saldo_a_favor'] - jogador['saldo_contra']
    
    erro_validacao = session.pop('erro_validacao', None)
    
    return render_template(
        'index.html',
        grupos=session.get('grupos', []),
        confrontos=session.get('confrontos', []),
        valores_salvos=session.get('valores_salvos', {}),
        modo_torneio=modo_atual,
        erro_validacao=erro_validacao,
        modos_disponiveis=[
            {'value': '20j', 'text': '20 Jogadores (5 grupos de 4)'},
            {'value': '24j', 'text': '24 Jogadores (6 grupos de 4)'},
            {'value': '28j', 'text': '28 Jogadores (7 grupos de 4)'},
            {'value': '32j', 'text': '32 Jogadores (8 grupos de 4)'}
        ]
    )