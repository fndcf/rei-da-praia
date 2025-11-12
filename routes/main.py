"""Funções para as principais rotas"""
from datetime import datetime
from flask import Blueprint, render_template, session, current_app, redirect, url_for, request, jsonify
from database.models import Torneio, Jogador, Confronto, ConfrontoEliminatoria, JogadorPermanente, ParticipacaoTorneio
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
    """Injeta a função timestamp"""
    return {'timestamp': datetime.now().timestamp()}

@bp.context_processor
def inject_enumerate():
    """Injeta a função enumerate"""
    return dict(enumerate=enumerate)

@bp.route('/')
def home():
    """Função para a home page"""    
    log_route_access('home')
    
    # Buscar todos os torneios, ordenados pelo mais recente
    torneios = Torneio.query.order_by(Torneio.data_criacao.desc()).all()
    
    torneio_em_andamento_db = Torneio.query.filter_by(finalizado=False).first()
    torneio_em_andamento = torneio_em_andamento_db is not None
    modo_torneio_dict = {}
    
    # Define um mapeamento para o número de jogadores
    modos_descricao = {
        '16j': '16 Jogadores',
        '20j': '20 Jogadores',
        '24j': '24 Jogadores',
        '28j': '28 Jogadores',
        '32j': '32 Jogadores'
    }
    
    # Verificar se a sessão está sincronizada com o banco
    torneio_id_sessao = session.get('torneio_id')
    
    if torneio_em_andamento_db:
        # Se existe torneio em andamento no banco, garantir que está na sessão
        if torneio_id_sessao != torneio_em_andamento_db.id:
            current_app.logger.info(
                f"Sincronizando sessão com torneio em andamento: {torneio_em_andamento_db.id}"
            )
            # Limpar sessão antiga se houver
            for key in ['torneio_id', 'grupos', 'confrontos', 'jogadores', 'valores_salvos', 'nome_torneio']:
                session.pop(key, None)
    else:
        # Se não há torneio em andamento no banco mas há ID na sessão, limpar
        if torneio_id_sessao:
            current_app.logger.warning(
                f"Torneio ID {torneio_id_sessao} não encontrado ou já finalizado. Limpando sessão."
            )
            for key in ['torneio_id', 'grupos', 'confrontos', 'jogadores', 'valores_salvos', 'nome_torneio']:
                session.pop(key, None)
    
    # Para cada torneio, recuperar campeões e vice-campeões e modo do torneio
    for torneio in torneios:

        # Contar jogadores para determinar o modo
        jogadores_count = Jogador.query.filter_by(torneio_id=torneio.id).count()
        
        if jogadores_count <= 16:
            modo_torneio_dict[torneio.id] = modos_descricao['16j']
        elif jogadores_count <= 20:
            modo_torneio_dict[torneio.id] = modos_descricao['20j']
        elif jogadores_count <= 24:
            modo_torneio_dict[torneio.id] = modos_descricao['24j']
        elif jogadores_count <= 28:
            modo_torneio_dict[torneio.id] = modos_descricao['28j']
        else:
            modo_torneio_dict[torneio.id] = modos_descricao['32j']

        if torneio.finalizado:
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
        else:
            torneio.campeoes = None
            torneio.vice_campeoes = None
    
    # Obter o ranking de jogadores
    ranking_jogadores = RankingManager.obter_ranking()
    
    # Limitar para os top 10 jogadores, se necessário
    ranking_jogadores = ranking_jogadores[:10] if len(ranking_jogadores) > 10 else ranking_jogadores
    
    # Mensagens de sucesso ou erro
    erro_validacao = session.pop('erro_validacao', None)
    sucesso_validacao = session.pop('sucesso_validacao', None)
    
    return render_template('home.html', 
                          torneios=torneios,
                          ranking_jogadores=ranking_jogadores,
                          erro_validacao=erro_validacao,
                          sucesso_validacao=sucesso_validacao,
                          torneio_em_andamento=torneio_em_andamento,
                          modo_torneio_dict=modo_torneio_dict)

def carregar_torneio_na_sessao(torneio_id):
    """Carrega torneio do banco e popula a sessão"""
    try:
        current_app.logger.info(f"🔄 Iniciando carregamento do torneio {torneio_id} na sessão")
        
        torneio = Torneio.query.get(torneio_id)
        if not torneio:
            current_app.logger.error(f"❌ Torneio {torneio_id} não encontrado")
            return False
        
        # Buscar jogadores
        jogadores = Jogador.query.filter_by(torneio_id=torneio_id).all()
        current_app.logger.info(f"📊 Encontrados {len(jogadores)} jogadores")
        
        # Determinar modo
        num_jogadores = len(jogadores)
        if num_jogadores <= 16:
            modo, num_grupos = '16j', 4
        elif num_jogadores <= 20:
            modo, num_grupos = '20j', 5
        elif num_jogadores <= 24:
            modo, num_grupos = '24j', 6
        elif num_jogadores <= 28:
            modo, num_grupos = '28j', 7
        else:
            modo, num_grupos = '32j', 8
        
        # Organizar jogadores por grupo
        jogadores_por_grupo = {}
        for jogador in jogadores:
            grupo_idx = jogador.grupo_idx
            if grupo_idx not in jogadores_por_grupo:
                jogadores_por_grupo[grupo_idx] = []
            
            jogadores_por_grupo[grupo_idx].append({
                'nome': jogador.nome,
                'id': jogador.id,
                'vitorias': jogador.vitorias,
                'saldo_a_favor': jogador.saldo_a_favor,
                'saldo_contra': jogador.saldo_contra,
                'saldo_total': jogador.saldo_total
            })
        
        current_app.logger.info(f"👥 Grupos organizados: {len(jogadores_por_grupo)} grupos")
        
        # Ordenar jogadores
        for grupo_idx in jogadores_por_grupo:
            jogadores_por_grupo[grupo_idx].sort(
                key=lambda x: (-x['vitorias'], -x['saldo_total'])
            )
        
        # Criar estrutura de grupos
        grupos = []
        for grupo_idx in sorted(jogadores_por_grupo.keys()):
            grupos.append(jogadores_por_grupo[grupo_idx])
        
        # Criar dicionário de jogadores
        jogadores_dict = {}
        for jogador in jogadores:
            jogadores_dict[jogador.nome] = {
                'nome': jogador.nome,
                'id': jogador.id,
                'vitorias': jogador.vitorias,
                'saldo_a_favor': jogador.saldo_a_favor,
                'saldo_contra': jogador.saldo_contra,
                'saldo_total': jogador.saldo_total
            }
        
        # Buscar e organizar confrontos
        confrontos_db = Confronto.query.filter_by(
            torneio_id=torneio_id
        ).order_by(Confronto.grupo_idx, Confronto.confronto_idx).all()
        
        current_app.logger.info(f"⚔️ Encontrados {len(confrontos_db)} confrontos")
        
        confrontos = [[] for _ in range(num_grupos)]
        valores_salvos = {}
        resultados_carregados = 0
        
        for confronto in confrontos_db:
            grupo_idx = confronto.grupo_idx
            confronto_idx = confronto.confronto_idx
            
            jogador_a1 = Jogador.query.get(confronto.jogador_a1_id)
            jogador_a2 = Jogador.query.get(confronto.jogador_a2_id)
            jogador_b1 = Jogador.query.get(confronto.jogador_b1_id)
            jogador_b2 = Jogador.query.get(confronto.jogador_b2_id)
            
            if all([jogador_a1, jogador_a2, jogador_b1, jogador_b2]):
                confrontos[grupo_idx].append((
                    jogadores_dict[jogador_a1.nome],
                    jogadores_dict[jogador_a2.nome],
                    jogadores_dict[jogador_b1.nome],
                    jogadores_dict[jogador_b2.nome]
                ))
                
                if confronto.pontos_dupla_a is not None:
                    campo_a = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaA_favor"
                    valores_salvos[campo_a] = str(confronto.pontos_dupla_a)
                    resultados_carregados += 1
                
                if confronto.pontos_dupla_b is not None:
                    campo_b = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaB_favor"
                    valores_salvos[campo_b] = str(confronto.pontos_dupla_b)
                    resultados_carregados += 1
        
        current_app.logger.info(f"📝 {resultados_carregados} resultados carregados")
        
        # Popular sessão
        session['torneio_id'] = torneio_id
        session['nome_torneio'] = torneio.nome
        session['modo_torneio'] = modo
        session['formato_eliminatoria'] = torneio.formato_eliminatoria or 'separados'
        session['jogadores'] = jogadores_dict
        session['grupos'] = grupos
        session['confrontos'] = confrontos
        session['valores_salvos'] = valores_salvos
        
        # ⚠️ CRÍTICO: Marcar a sessão como modificada
        session.modified = True
        
        current_app.logger.info(f"✅ Torneio {torneio_id} carregado na sessão com sucesso!")
        current_app.logger.info(f"   - {len(grupos)} grupos")
        current_app.logger.info(f"   - {len(jogadores_dict)} jogadores")
        current_app.logger.info(f"   - {len(valores_salvos)} valores salvos")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Erro ao carregar torneio {torneio_id}: {str(e)}", exc_info=True)
        return False

@bp.route('/novo-torneio')
def novo_torneio():
    """Função para criar um novo torneio"""
    try:
        # Inicialização de sessão
        session.setdefault('valores_salvos', {})
        modos_validos = ['16j','20j', '24j', '28j', '32j']
        modo_atual = session.get('modo_torneio', '28j')
        
        torneio_em_andamento_db = Torneio.query.filter_by(finalizado=False).first()
        torneio_em_andamento = torneio_em_andamento_db is not None
        nome_torneio = ""
        
        if torneio_em_andamento_db:
            # Se existe torneio em andamento, carregar seus dados
            torneio_id = torneio_em_andamento_db.id
            nome_torneio = torneio_em_andamento_db.nome
            
            # Sincronizar sessão com o torneio do banco
            torneio_id_sessao = session.get('torneio_id')
            
            if torneio_id_sessao != torneio_id:
                current_app.logger.info(f"🔄 Sessão desatualizada. Sessão: {torneio_id_sessao}, Banco: {torneio_id}")
                sucesso = carregar_torneio_na_sessao(torneio_id)
                if sucesso:
                    current_app.logger.info(f"✅ Torneio {torneio_id} sincronizado com sucesso")
                else:
                    current_app.logger.error(f"❌ Falha ao sincronizar torneio {torneio_id}")
            elif not session.get('grupos'):
                # Se tem torneio mas não tem grupos, carregar
                current_app.logger.info(f"🔄 Torneio {torneio_id} na sessão mas grupos vazios. Recarregando...")
                carregar_torneio_na_sessao(torneio_id)
            else:
                current_app.logger.info(f"✅ Sessão já sincronizada com torneio {torneio_id}")
        else:
            # Se não há torneio em andamento no banco mas há ID na sessão, limpar
            torneio_id_sessao = session.get('torneio_id')
            if torneio_id_sessao:
                current_app.logger.warning(
                    f"Torneio ID {torneio_id_sessao} não encontrado ou já finalizado. Limpando sessão."
                )
                for key in ['torneio_id', 'grupos', 'confrontos', 'jogadores', 'valores_salvos', 'nome_torneio']:
                    session.pop(key, None)
        
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
            for nome, jogador in session['jogadores'].items():
                jogador.setdefault('vitorias', 0)
                jogador.setdefault('saldo_a_favor', 0)
                jogador.setdefault('saldo_contra', 0)
                jogador['saldo_total'] = jogador['saldo_a_favor'] - jogador['saldo_contra']

        return render_template(
            'sorteio-grupos.html',
            grupos=session.get('grupos', []),
            confrontos=session.get('confrontos', []),
            valores_salvos=session.get('valores_salvos', {}),
            modo_torneio=modo_atual,
            torneio_em_andamento=torneio_em_andamento,
            nome_torneio=nome_torneio,
            modos_disponiveis=[
                {'value': '16j', 'text': '16 Jogadores (4 grupos de 4)'},
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
    """Função para fazer os detalhes do torneio"""
    log_route_access(f'detalhes-torneio/{torneio_id}')
    
    # Buscar o torneio pelo ID
    torneio = Torneio.query.get_or_404(torneio_id)
    
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
        4: '16j',
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
        modo_torneio=modo_torneio,
        torneio_em_andamento=not torneio.finalizado
    )

@bp.route('/buscar_jogadores', methods=['GET'])
def buscar_jogadores():
    """Endpoint AJAX para buscar jogadores por nome"""
    termo = request.args.get('termo', '')
    if len(termo) < 2:
        return jsonify([])
    
    # Buscar jogadores que contenham o termo pesquisado
    jogadores = JogadorPermanente.query.filter(
        JogadorPermanente.nome.ilike(f'%{termo}%')
    ).order_by(JogadorPermanente.nome).limit(10).all()
    
    # Formatando resultado
    resultados = [{'id': j.id, 'nome': j.nome} for j in jogadores]
    
    return jsonify(resultados)

@bp.route('/perfil_jogador', methods=['GET'])
def perfil_jogador():
    """Função para fazer o perfil do jogador"""
    log_route_access('perfil_jogador')
    
    # Obter o nome do jogador da query string
    nome_jogador = request.args.get('nome_jogador', '').strip()
    
    if not nome_jogador:
        return render_template(
            'jogador_nao_encontrado.html',
            mensagem="Por favor, informe o nome do jogador para pesquisa."
        )
    
    # Buscar o jogador permanente
    jogador = JogadorPermanente.query.filter(JogadorPermanente.nome.ilike(f"%{nome_jogador}%")).first()
    
    if not jogador:
        # Tentar encontrar jogadores similares para sugestão
        jogadores_similares = JogadorPermanente.query.filter(
            JogadorPermanente.nome.ilike(f"%{nome_jogador.split()[0] if ' ' in nome_jogador else nome_jogador}%")
        ).limit(5).all()
        
        return render_template(
            'jogador_nao_encontrado.html',
            termo_pesquisa=nome_jogador,
            jogadores_similares=jogadores_similares
        )
    
    # Estatísticas gerais
    total_jogos = 0
    total_vitorias = 0
    
    # Obter o ranking completo
    ranking = RankingManager.obter_ranking()
    
    # Encontrar a posição e pontuação do jogador no ranking
    posicao_ranking = None
    total_pontos = 0
    for r in ranking:
        if r['nome'] == jogador.nome:
            posicao_ranking = r['posicao']
            total_pontos = r['pontos']
            break
    
    # Buscar todas as participações do jogador
    participacoes = db.session.query(
        ParticipacaoTorneio, Torneio, Jogador
    ).join(
        Torneio, ParticipacaoTorneio.torneio_id == Torneio.id
    ).join(
        Jogador, (Jogador.torneio_id == Torneio.id) & (Jogador.jogador_permanente_id == jogador.id)
    ).filter(
        ParticipacaoTorneio.jogador_permanente_id == jogador.id
    ).all()
    
    # Processar cada participação para calcular estatísticas
    participacoes_detalhadas = []
    for participacao, torneio, jogador_torneio in participacoes:
        # Jogos da fase de grupos (3 jogos por grupo)
        jogos_grupo = 3
        
        # Buscar confrontos eliminatórias onde o jogador participou
        confrontos_eliminatorias = ConfrontoEliminatoria.query.filter(
            ConfrontoEliminatoria.torneio_id == torneio.id,
            db.or_(
                ConfrontoEliminatoria.jogador_a1_id == jogador_torneio.id,
                ConfrontoEliminatoria.jogador_a2_id == jogador_torneio.id,
                ConfrontoEliminatoria.jogador_b1_id == jogador_torneio.id,
                ConfrontoEliminatoria.jogador_b2_id == jogador_torneio.id
            )
        ).all()
        
        # Contar vitórias nas eliminatórias
        vitorias_eliminatorias = 0
        for confronto in confrontos_eliminatorias:
            # Verificar se o jogador estava no time vencedor
            jogador_no_time_a = (confronto.jogador_a1_id == jogador_torneio.id or 
                                confronto.jogador_a2_id == jogador_torneio.id)
            time_a_venceu = confronto.pontos_dupla_a > confronto.pontos_dupla_b
            
            if (jogador_no_time_a and time_a_venceu) or (not jogador_no_time_a and not time_a_venceu):
                vitorias_eliminatorias += 1
        
        jogos_eliminatorias = len(confrontos_eliminatorias)
        vitorias_total = participacao.vitorias + vitorias_eliminatorias
        jogos_torneio = jogos_grupo + jogos_eliminatorias
        
        # Atualizar estatísticas gerais
        total_jogos += jogos_torneio
        total_vitorias += vitorias_total
        
        # Adicionar detalhes desta participação
        participacoes_detalhadas.append({
            'torneio_id': torneio.id,
            'jogador_id': jogador_torneio.id,
            'torneio': torneio.nome,
            'data': torneio.data_criacao.strftime('%d/%m/%Y'),
            'jogos': jogos_torneio,
            'vitorias': vitorias_total,
            'vitorias_grupo': participacao.vitorias,
            'vitorias_eliminatorias': vitorias_eliminatorias,
            'pontuacao': jogador_torneio.pontuacao,
            'finalizado': torneio.finalizado
        })
    
    # Ordenar as participações por data (mais recentes primeiro)
    participacoes_detalhadas.sort(key=lambda x: x['data'], reverse=True)
    
    return render_template(
        'perfil_jogador.html',
        jogador=jogador,
        participacoes=participacoes_detalhadas,
        total_jogos=total_jogos,
        total_vitorias=total_vitorias,
        total_pontos=total_pontos,
        posicao_ranking=posicao_ranking
    )

@bp.route('/detalhes_jogador/<int:torneio_id>/<int:jogador_id>', methods=['GET'])
def detalhes_jogador(torneio_id, jogador_id):
    """Função para fazer os detalhes do jogador"""
    log_route_access(f'detalhes_jogador/{torneio_id}/{jogador_id}')
    
    # Buscar o jogador e o torneio
    jogador = Jogador.query.get_or_404(jogador_id)
    torneio = Torneio.query.get_or_404(torneio_id)
    jogador_permanente = JogadorPermanente.query.get(jogador.jogador_permanente_id)
    
    # Buscar os confrontos da fase de grupos
    confrontos_grupo = Confronto.query.filter(
        Confronto.torneio_id == torneio_id,
        db.or_(
            Confronto.jogador_a1_id == jogador_id,
            Confronto.jogador_a2_id == jogador_id,
            Confronto.jogador_b1_id == jogador_id,
            Confronto.jogador_b2_id == jogador_id
        )
    ).order_by(Confronto.grupo_idx, Confronto.confronto_idx).all()
    
    # Buscar os confrontos da fase eliminatória
    confrontos_eliminatorias = ConfrontoEliminatoria.query.filter(
        ConfrontoEliminatoria.torneio_id == torneio_id,
        db.or_(
            ConfrontoEliminatoria.jogador_a1_id == jogador_id,
            ConfrontoEliminatoria.jogador_a2_id == jogador_id,
            ConfrontoEliminatoria.jogador_b1_id == jogador_id,
            ConfrontoEliminatoria.jogador_b2_id == jogador_id
        )
    ).all()
    
    # Mapear todos os jogadores para facilitar o acesso
    jogadores_ids = set()
    for c in confrontos_grupo:
        jogadores_ids.update([c.jogador_a1_id, c.jogador_a2_id, c.jogador_b1_id, c.jogador_b2_id])
    
    for c in confrontos_eliminatorias:
        jogadores_ids.update([c.jogador_a1_id, c.jogador_a2_id, c.jogador_b1_id, c.jogador_b2_id])
    
    jogadores_map = {j.id: j for j in Jogador.query.filter(Jogador.id.in_(jogadores_ids)).all()}
    
    # Processar os confrontos de grupo para fácil exibição
    confrontos_grupo_data = []
    for c in confrontos_grupo:
        jogador_no_time_a = (c.jogador_a1_id == jogador_id or c.jogador_a2_id == jogador_id)
        
        if jogador_no_time_a:
            parceiro_id = c.jogador_a1_id if c.jogador_a2_id == jogador_id else c.jogador_a2_id
            adversario1_id = c.jogador_b1_id
            adversario2_id = c.jogador_b2_id
            pontos_equipe = c.pontos_dupla_a
            pontos_adversarios = c.pontos_dupla_b
        else:
            parceiro_id = c.jogador_b1_id if c.jogador_b2_id == jogador_id else c.jogador_b2_id
            adversario1_id = c.jogador_a1_id
            adversario2_id = c.jogador_a2_id
            pontos_equipe = c.pontos_dupla_b
            pontos_adversarios = c.pontos_dupla_a
        
        resultado = "Vitória" if pontos_equipe > pontos_adversarios else "Derrota" if pontos_equipe < pontos_adversarios else "Empate"
        
        confrontos_grupo_data.append({
            'grupo': c.grupo_idx + 1,
            'confronto': c.confronto_idx + 1,
            'parceiro': jogadores_map[parceiro_id].nome,
            'adversario1': jogadores_map[adversario1_id].nome,
            'adversario2': jogadores_map[adversario2_id].nome,
            'pontos_equipe': pontos_equipe,
            'pontos_adversarios': pontos_adversarios,
            'resultado': resultado
        })
    
    # Processar os confrontos eliminatórios
    confrontos_eliminatorias_data = []
    for c in confrontos_eliminatorias:
        jogador_no_time_a = (c.jogador_a1_id == jogador_id or c.jogador_a2_id == jogador_id)
        
        if jogador_no_time_a:
            parceiro_id = c.jogador_a1_id if c.jogador_a2_id == jogador_id else c.jogador_a2_id
            adversario1_id = c.jogador_b1_id
            adversario2_id = c.jogador_b2_id
            pontos_equipe = c.pontos_dupla_a
            pontos_adversarios = c.pontos_dupla_b
        else:
            parceiro_id = c.jogador_b1_id if c.jogador_b2_id == jogador_id else c.jogador_b2_id
            adversario1_id = c.jogador_a1_id
            adversario2_id = c.jogador_a2_id
            pontos_equipe = c.pontos_dupla_b
            pontos_adversarios = c.pontos_dupla_a
        
        resultado = "Vitória" if pontos_equipe > pontos_adversarios else "Derrota" if pontos_equipe < pontos_adversarios else "Empate"
        
        confrontos_eliminatorias_data.append({
            'fase': c.fase.capitalize(),
            'jogo': c.jogo_numero,
            'parceiro': jogadores_map[parceiro_id].nome,
            'adversario1': jogadores_map[adversario1_id].nome,
            'adversario2': jogadores_map[adversario2_id].nome,
            'pontos_equipe': pontos_equipe,
            'pontos_adversarios': pontos_adversarios,
            'resultado': resultado
        })

    # Ordenar os confrontos pela ordem correta das fases
    ordem_fases = {"Quartas": 1, "Semi": 2, "Final": 3}
    confrontos_eliminatorias_data.sort(key=lambda c: ordem_fases.get(c['fase'], 0))
    
    return render_template(
        'detalhes_jogador.html',
        jogador=jogador,
        jogador_permanente=jogador_permanente,
        torneio=torneio,
        confrontos_grupo=confrontos_grupo_data,
        confrontos_eliminatorias=confrontos_eliminatorias_data
    )

@bp.route('/apagar_torneio/<int:torneio_id>', methods=['POST'])
def apagar_torneio(torneio_id):
    """Função para apagar torneio em andamento"""
    log_route_access(f'apagar_torneio/{torneio_id}')
    
    # Verificar se o torneio existe
    torneio = Torneio.query.get_or_404(torneio_id)
    
    try:
        # Verificar se o torneio está finalizado
        if torneio.finalizado:
            session['erro_validacao'] = "Não é possível apagar um torneio finalizado."
            return redirect(url_for('main.home'))
        
        # Obter o nome do torneio para mensagem de confirmação
        nome_torneio = torneio.nome
        
        # Deletar confrontos associados
        Confronto.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar confrontos eliminatórias associados
        ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar jogadores associados
        Jogador.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar participações associadas
        ParticipacaoTorneio.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar o torneio
        db.session.delete(torneio)
        
        # Commit das mudanças
        db.session.commit()
        
        # Limpar variáveis de sessão se for o torneio atual
        if session.get('torneio_id') == torneio_id:
            session['torneio_id'] = None
            session['grupos'] = []
            session['confrontos'] = []
            session['jogadores'] = {}
            session['valores_salvos'] = {}
        
        session['sucesso_validacao'] = f"Torneio '{nome_torneio}' apagado com sucesso."
        return redirect(url_for('main.home'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao apagar torneio: {str(e)}", exc_info=True)
        session['erro_validacao'] = f"Erro ao apagar torneio: {str(e)}"
        return redirect(url_for('main.home'))

@bp.route('/cancelar_torneio')
def cancelar_torneio():
    """Cancela o torneio atual e remove todos os dados relacionados"""
    log_route_access('cancelar_torneio')
    
    torneio_id = session.get('torneio_id')
    if not torneio_id:
        session['erro_validacao'] = "Nenhum torneio ativo para cancelar."
        return redirect(url_for('main.home'))
    
    try:
        # Buscar o torneio
        torneio = Torneio.query.get(torneio_id)
        if not torneio:
            session['erro_validacao'] = "Torneio não encontrado."
            return redirect(url_for('main.home'))
        
        # Verificar se o torneio está finalizado
        if torneio.finalizado:
            session['erro_validacao'] = "Não é possível cancelar um torneio finalizado."
            return redirect(url_for('main.home'))
        
        nome_torneio = torneio.nome
        
        # Deletar confrontos de eliminatórias
        ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar confrontos
        Confronto.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar jogadores e participações
        Jogador.query.filter_by(torneio_id=torneio_id).delete()
        ParticipacaoTorneio.query.filter_by(torneio_id=torneio_id).delete()
        
        # Deletar o torneio
        db.session.delete(torneio)
        db.session.commit()
        
        # Limpar a sessão
        session['torneio_id'] = None
        session['grupos'] = []
        session['confrontos'] = []
        session['jogadores'] = {}
        session['valores_salvos'] = {}
        
        session['sucesso_validacao'] = f"Torneio '{nome_torneio}' cancelado com sucesso."
        return redirect(url_for('main.home'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao cancelar torneio: {str(e)}", exc_info=True)
        session['erro_validacao'] = f"Erro ao cancelar torneio: {str(e)}"
        return redirect(url_for('main.novo_torneio'))
    
@bp.route('/listar_todos_jogadores', methods=['GET'])
def listar_todos_jogadores():
    """Endpoint AJAX para listar todos os jogadores cadastrados"""
    try:
        # Buscar todos os jogadores permanentes
        jogadores = JogadorPermanente.query.order_by(JogadorPermanente.nome).limit(100).all()
        
        # Formatando resultado
        resultados = [{'id': j.id, 'nome': j.nome} for j in jogadores]
        
        return jsonify(resultados)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar jogadores: {str(e)}", exc_info=True)
        return jsonify([])
    
@bp.route('/ranking-completo')
def ranking_completo():
    """Função para fazer o ranking de jogadores completo, sem limitação de 10 jogadores"""
    log_route_access('ranking_completo')
    
    # Obter o ranking completo de jogadores
    ranking_jogadores = RankingManager.obter_ranking()
    
    return render_template(
        'ranking_completo.html',
        ranking_jogadores=ranking_jogadores,
        titulo="Ranking Completo de Jogadores"
    )