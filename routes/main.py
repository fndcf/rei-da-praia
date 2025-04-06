from flask import Blueprint, render_template, session, current_app
from datetime import datetime

bp = Blueprint('main', __name__)

def log_route_access(route_name):
    """Log de acesso a rotas principais"""
    current_app.logger.info(
        f"Route accessed: {route_name} | "
        f"Session keys: {list(session.keys())} | "
        f"Modo: {session.get('modo_torneio', 'none')}"
    )

@bp.context_processor
def inject_timestamp():
    return {'timestamp': datetime.now().timestamp()}

@bp.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@bp.route('/')
def index():
    try:
        # Inicialização de sessão
        session.setdefault('valores_salvos', {})
        modos_validos = ['20j', '24j', '28j', '32j']
        modo_atual = session.get('modo_torneio', '28j')
        
        # Validação do modo
        if modo_atual not in modos_validos:
            current_app.logger.warning(
                f"Modo inválido resetado: {modo_atual} -> 28j"
            )
            modo_atual = '28j'
            session['modo_torneio'] = modo_atual

        # Log de acesso à rota
        log_route_access('index')
        
        # Atualização de jogadores
        if 'jogadores' in session:
            player_count = len(session['jogadores'])
            current_app.logger.debug(
                f"Atualizando {player_count} jogadores na sessão"
            )
            
            for nome, jogador in session['jogadores'].items():
                jogador.setdefault('vitorias', 0)
                jogador.setdefault('saldo_a_favor', 0)
                jogador.setdefault('saldo_contra', 0)
                jogador['saldo_total'] = jogador['saldo_a_favor'] - jogador['saldo_contra']

        # Log de erros de validação
        erro_validacao = session.pop('erro_validacao', None)
        if erro_validacao:
            current_app.logger.error(
                f"Erro de validação exibido: {erro_validacao}"
            )

        # Log antes do render
        current_app.logger.debug(
            f"Renderizando index | "
            f"Grupos: {len(session.get('grupos', []))} | "
            f"Confrontos: {len(session.get('confrontos', []))}"
        )
        
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

    except Exception as e:
        current_app.logger.critical(
            f"Falha crítica na rota principal: {str(e)}",
            exc_info=True
        )
        raise  # Re-lança a exceção para o handler do Flask