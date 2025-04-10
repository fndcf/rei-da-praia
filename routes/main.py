from flask import Blueprint, render_template, session, current_app, redirect, url_for
from datetime import datetime
from database.models import Torneio, Jogador, Confronto, ConfrontoEliminatoria
from database.ranking import RankingManager
from database.db import db

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
def home():
    log_route_access('home')
    
    # Buscar todos os torneios finalizados
    torneios_finalizados = Torneio.query.filter_by(finalizado=True).order_by(Torneio.data_criacao.desc()).all()
    
    # Para cada torneio, recuperar campeões e vice-campeões
    for torneio in torneios_finalizados:
        # Buscar confronto da final
        final = ConfrontoEliminatoria.query.filter_by(
            torneio_id=torneio.id,
            fase='final'
        ).first()
        
        if final:
            # Determinar campeões e vice-campeões
            jogador_a1 = Jogador.query.get(final.jogador_a1_id)
            jogador_a2 = Jogador.query.get(final.jogador_a2_id)
            jogador_b1 = Jogador.query.get(final.jogador_b1_id)
            jogador_b2 = Jogador.query.get(final.jogador_b2_id)
            
            # Determinar quem é o campeão e quem é o vice
            if final.pontos_dupla_a > final.pontos_dupla_b:
                torneio.campeoes = [jogador_a1.nome, jogador_a2.nome]
                torneio.vice_campeoes = [jogador_b1.nome, jogador_b2.nome]
            else:
                torneio.campeoes = [jogador_b1.nome, jogador_b2.nome]
                torneio.vice_campeoes = [jogador_a1.nome, jogador_a2.nome]
        else:
            torneio.campeoes = None
            torneio.vice_campeoes = None
    
    # Obter o ranking de jogadores
    ranking_jogadores = RankingManager.obter_ranking()
    
    # Limitar para os top 10 jogadores, se necessário
    ranking_jogadores = ranking_jogadores[:10] if len(ranking_jogadores) > 10 else ranking_jogadores
    
    return render_template('home.html', 
                          torneios_finalizados=torneios_finalizados,
                          ranking_jogadores=ranking_jogadores)

@bp.route('/novo-torneio')
def novo_torneio():
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
        log_route_access('novo-torneio')
        
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
            f"Renderizando novo-torneio | "
            f"Grupos: {len(session.get('grupos', []))} | "
            f"Confrontos: {len(session.get('confrontos', []))}"
        )
        
        return render_template(
            'sorteio-grupos.html',
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

@bp.route('/detalhes-torneio/<int:torneio_id>')
def detalhes_torneio(torneio_id):
    log_route_access(f'detalhes-torneio/{torneio_id}')
    
    # Buscar o torneio pelo ID
    torneio = Torneio.query.get_or_404(torneio_id)
    
    # Verificar se o torneio está finalizado
    if not torneio.finalizado:
        current_app.logger.warning(f"Tentativa de acessar detalhes de torneio não finalizado: {torneio_id}")
        return redirect(url_for('main.home'))
    
    # Buscar todos os jogadores do torneio
    jogadores = Jogador.query.filter_by(torneio_id=torneio_id).all()
    
    # Organizar jogadores por grupos
    # Precisamos recuperar os confrontos para identificar os grupos
    confrontos = Confronto.query.filter_by(torneio_id=torneio_id).all()
    
    # Dicionário para armazenar grupos e confrontos
    grupos = {}
    jogadores_por_grupo = {}
    
    # Primeiro, identificar quais jogadores pertencem a cada grupo
    for confronto in confrontos:
        grupo_idx = confronto.grupo_idx
        
        if grupo_idx not in jogadores_por_grupo:
            jogadores_por_grupo[grupo_idx] = set()
            grupos[grupo_idx] = {
                'confrontos': [],
                'jogadores_ordenados': []
            }
        
        # Adicionar jogadores ao grupo
        jogadores_ids = [
            confronto.jogador_a1_id, 
            confronto.jogador_a2_id, 
            confronto.jogador_b1_id, 
            confronto.jogador_b2_id
        ]
        
        for jogador_id in jogadores_ids:
            jogadores_por_grupo[grupo_idx].add(jogador_id)
        
        # Adicionar o confronto ao grupo
        grupos[grupo_idx]['confrontos'].append(confronto)
    
    # Mapear jogadores para facilitar a exibição
    jogadores_map = {jogador.id: jogador for jogador in jogadores}
    
    # Para cada grupo, calcular manualmente as estatísticas dos jogadores
    for grupo_idx, jogadores_ids in jogadores_por_grupo.items():
        # Inicializar estatísticas para cada jogador
        estatisticas = {jogador_id: {
            'id': jogador_id,
            'nome': jogadores_map[jogador_id].nome,
            'vitorias': 0,
            'saldo_a_favor': 0,
            'saldo_contra': 0,
            'saldo_total': 0,
            'posicao_grupo': jogadores_map[jogador_id].posicao_grupo
        } for jogador_id in jogadores_ids}
        
        # Processar todos os confrontos do grupo para calcular as estatísticas
        for confronto in grupos[grupo_idx]['confrontos']:
            # Só processa se o confronto tiver resultados
            if confronto.pontos_dupla_a is not None and confronto.pontos_dupla_b is not None:
                # Jogadores da dupla A
                for jogador_id in [confronto.jogador_a1_id, confronto.jogador_a2_id]:
                    estatisticas[jogador_id]['saldo_a_favor'] += confronto.pontos_dupla_a
                    estatisticas[jogador_id]['saldo_contra'] += confronto.pontos_dupla_b
                    if confronto.pontos_dupla_a > confronto.pontos_dupla_b:
                        estatisticas[jogador_id]['vitorias'] += 1
                
                # Jogadores da dupla B
                for jogador_id in [confronto.jogador_b1_id, confronto.jogador_b2_id]:
                    estatisticas[jogador_id]['saldo_a_favor'] += confronto.pontos_dupla_b
                    estatisticas[jogador_id]['saldo_contra'] += confronto.pontos_dupla_a
                    if confronto.pontos_dupla_b > confronto.pontos_dupla_a:
                        estatisticas[jogador_id]['vitorias'] += 1
        
        # Calcular saldo total
        for jogador_id in estatisticas:
            estatisticas[jogador_id]['saldo_total'] = estatisticas[jogador_id]['saldo_a_favor'] - estatisticas[jogador_id]['saldo_contra']
        
        # Converter para lista e ordenar
        jogadores_stats = list(estatisticas.values())
        
        # Tentar usar a posição salva ou ordenar pelas estatísticas calculadas
        if all(j['posicao_grupo'] > 0 for j in jogadores_stats):
            # Se todos os jogadores têm posição definida, usar isso
            jogadores_stats.sort(key=lambda x: x['posicao_grupo'])
        else:
            # Senão, ordenar por vitórias e saldo total
            jogadores_stats.sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
        
        grupos[grupo_idx]['jogadores_ordenados'] = jogadores_stats
    
    # Buscar confrontos da fase eliminatória
    confrontos_eliminatorias = ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).all()
    
    # Organizar os confrontos por fase
    fases_eliminatorias = {
        'quartas': [],
        'semi': [],
        'final': None
    }
    
    for confronto in confrontos_eliminatorias:
        if confronto.fase == 'final':
            fases_eliminatorias['final'] = confronto
        else:
            fases_eliminatorias[confronto.fase].append(confronto)
    
    # Determinar campeões e vice-campeões
    final = fases_eliminatorias['final']
    campeoes = None
    vice_campeoes = None
    placar_final = None
    
    if final:
        jogador_a1 = Jogador.query.get(final.jogador_a1_id)
        jogador_a2 = Jogador.query.get(final.jogador_a2_id)
        jogador_b1 = Jogador.query.get(final.jogador_b1_id)
        jogador_b2 = Jogador.query.get(final.jogador_b2_id)
        
        if final.pontos_dupla_a > final.pontos_dupla_b:
            campeoes = [jogador_a1, jogador_a2]
            vice_campeoes = [jogador_b1, jogador_b2]
        else:
            campeoes = [jogador_b1, jogador_b2]
            vice_campeoes = [jogador_a1, jogador_a2]
            
        placar_final = f"{final.pontos_dupla_a}x{final.pontos_dupla_b}"
    
    # Calcular o modo do torneio baseado no número de grupos
    modo_torneio = {
        5: '20j',
        6: '24j',
        7: '28j',
        8: '32j'
    }.get(len(grupos), '28j')
    
    return render_template(
        'detalhes_torneio.html',
        torneio=torneio,
        grupos=grupos,
        jogadores=jogadores_map,
        quartas=fases_eliminatorias['quartas'],
        semis=fases_eliminatorias['semi'],
        final=fases_eliminatorias['final'],
        campeoes=campeoes,
        vice_campeoes=vice_campeoes,
        placar_final=placar_final,
        modo_torneio=modo_torneio
    )