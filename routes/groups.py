"""Funções para criação de grupos"""
import random
import re
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, session, current_app, jsonify
from database.models import Jogador, Torneio, Confronto, JogadorPermanente, ParticipacaoTorneio
from database.db import db


bp = Blueprint('groups', __name__)

def log_action(action, details):
    """Função auxiliar para padronizar logs"""
    current_app.logger.info(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{action.upper()} - {details}"
    )

def criar_jogador(nome):
    """Função para criar jogador"""
    jogador = {
        'nome': nome,
        'vitorias': 0,
        'saldo_a_favor': 0,
        'saldo_contra': 0,
        'saldo_total': 0
    }
    log_action("player_created", f"Jogador: {nome}")
    return jogador

def criar_grupos(jogadores, modo, cabecas_de_chave=None):
    """Divide os jogadores em grupos de 4 com logging, considerando cabeças de chave"""
    num_groups = {
        '16j': (16, 4),
        '20j': (20, 5),
        '24j': (24, 6),
        '28j': (28, 7),
        '32j': (32, 8)
    }.get(modo, (28, 7))
    
    num_jogadores, num_grupos = num_groups
    grupos = [[] for _ in range(num_grupos)]
    
    # Se houver cabeças de chave, distribuir um por grupo primeiro
    if cabecas_de_chave:
        log_action("seeding_players", f"Distribuindo {len(cabecas_de_chave)} cabeças de chave")
        for i, cabeca in enumerate(cabecas_de_chave):
            if i < num_grupos:
                grupos[i].append(cabeca)
                log_action("seed_placed", f"Cabeça de chave {cabeca} no Grupo {i+1}")
        
        # Remover cabeças de chave da lista de jogadores
        jogadores = [j for j in jogadores if j not in cabecas_de_chave]
    
    # Embaralhar os jogadores restantes
    random.shuffle(jogadores)
    
    # Distribuir os jogadores restantes entre os grupos
    jogador_idx = 0
    for grupo in grupos:
        while len(grupo) < 4 and jogador_idx < len(jogadores):
            grupo.append(jogadores[jogador_idx])
            jogador_idx += 1
    
    log_action("groups_created", f"Modo: {modo} - {num_grupos} grupos criados com cabeças de chave")
    return grupos
    
def gerar_confrontos(grupo):
    """Gera os 3 confrontos do grupo com logging"""
    confrontos = [
        (grupo[0], grupo[1], grupo[2], grupo[3]),
        (grupo[0], grupo[2], grupo[1], grupo[3]),
        (grupo[0], grupo[3], grupo[1], grupo[2])
    ]
    log_action("matches_generated", f"Grupo com jogadores: {[j['nome'] for j in grupo]}")
    return confrontos

@bp.route('/sorteio', methods=['POST'])
def sorteio():
    """Função para fazer o sorteio do grupo"""
    try:

        # Verificar se já existe um torneio não finalizado no banco
        torneio_em_andamento = Torneio.query.filter_by(finalizado=False).first()

        if torneio_em_andamento:
            log_action("tournament_start_prevented", 
                      f"Tentativa de novo sorteio com torneio {torneio_em_andamento.id} em andamento")
            session['erro_validacao'] = (
                f"Já existe um torneio em andamento: '{torneio_em_andamento.nome}'. "
                f"Para realizar um novo sorteio, finalize ou cancele o torneio atual primeiro."
            )
            return redirect(url_for('main.novo_torneio'))

        # Verificar se já existem grupos sorteados
        if 'grupos' in session and session['grupos']:
            log_action("tournament_start_prevented", "Tentativa de novo sorteio com grupos existentes")
            session['erro_validacao'] = "Um sorteio já foi realizado. Para realizar um novo sorteio, cancele o torneio atual."
            return redirect(url_for('main.novo_torneio'))
            
        modo = request.form.get('modo_torneio', '28j')
        nome_torneio = request.form.get('nome_torneio', 'Torneio Sem Nome')
        # NOVO: Obter formato para todas as eliminatórias
        formato_eliminatoria = request.form.get('formato_eliminatoria', 'separados')
        log_action("tournament_start", f"Iniciando sorteio - Modo: {modo}, Formato: {formato_eliminatoria}")

        # Armazenar o nome do torneio na sessão para uso posterior
        session['nome_torneio'] = nome_torneio

        # Verifica se já existe um torneio com o mesmo nome
        torneio_existente = Torneio.query.filter_by(nome=nome_torneio).first()
        if torneio_existente:
            session['erro_validacao'] = f"Já existe um torneio com o nome '{nome_torneio}'. Por favor, escolha outro nome."
            return redirect(url_for('main.novo_torneio'))
        
        # Validação e processamento de nomes
        nomes = [nome.strip() for nome in request.form['jogadores'].split(',') 
                if nome.strip() and re.match(r'^[a-zA-ZÀ-ú0-9\s,]+$', nome.strip())]
        
        expected_players = {
            '16j': 16,'20j': 20, '24j': 24, 
            '28j': 28, '32j': 32
        }.get(modo, 28)
        
        if len(nomes) != expected_players:
            error_msg = f"Jogadores incorretos! Esperado: {expected_players}, Recebido: {len(nomes)}"
            current_app.logger.error(error_msg)
            session['erro_validacao'] = error_msg
            return redirect(url_for('main.novo_torneio'))
        
        # Cria novo torneio
        novo_torneio = Torneio(nome=nome_torneio, formato_eliminatoria=formato_eliminatoria)
        db.session.add(novo_torneio)
        db.session.flush()  # Para obter o ID sem fazer commit completo
        
        # Primeiro, garantir que todos os jogadores permanentes existam
        jogadores_permanentes = {}
        
        for nome in nomes:
            # Verificar se jogador já existe
            jogador = JogadorPermanente.query.filter_by(nome=nome).first()
            
            # Se não existe, criar
            if not jogador:
                jogador = JogadorPermanente(nome=nome)
                db.session.add(jogador)
                db.session.flush()  # Obter ID sem commit
                log_action("player_created_permanent", f"Novo jogador permanente: {nome} (ID: {jogador.id})")
            else:
                log_action("player_reused", f"Jogador existente: {nome} (ID: {jogador.id})")
                
            jogadores_permanentes[nome] = jogador
        
        # Agora criar participações e jogadores (para compatibilidade)
        participacoes = {}
        jogadores_dict = {}
        
        for nome in nomes:
            jogador_permanente = jogadores_permanentes[nome]
            
            # Criar participação
            participacao = ParticipacaoTorneio(
                jogador_permanente_id=jogador_permanente.id,
                torneio_id=novo_torneio.id
            )
            db.session.add(participacao)
            db.session.flush()  # Obter ID sem commit
            participacoes[nome] = participacao
            
            # Criar jogador para compatibilidade
            jogador = Jogador(
                nome=nome,
                torneio_id=novo_torneio.id,
                jogador_permanente_id=jogador_permanente.id
            )
            db.session.add(jogador)
            db.session.flush()  # Obter ID sem commit
            jogadores_dict[nome] = jogador
            
            log_action("player_participation_created", 
                      f"Participação criada: {nome} - Jogador ID: {jogador.id}, Participação ID: {participacao.id}")
        
        # Commit para garantir que todos os jogadores estejam salvos antes de gerar confrontos
        db.session.commit()
        
        # Estrutura de dados na sessão
        session.update({
            'torneio_id': novo_torneio.id,
            'modo_torneio': modo,
            'formato_eliminatoria': formato_eliminatoria,
            'jogadores': {
                nome: {
                    'nome': jogador.nome,
                    'id': jogador.id,
                    'vitorias': jogador.vitorias,
                    'saldo_a_favor': jogador.saldo_a_favor,
                    'saldo_contra': jogador.saldo_contra,
                    'saldo_total': jogador.saldo_total
                } for nome, jogador in jogadores_dict.items()
            },
            'grupos': [],
            'confrontos': [],
            'valores_salvos': {}
        })
        
        # Processar cabeças de chave se fornecidas
        cabecas_de_chave_nomes = []
        if 'cabecas_de_chave' in request.form and request.form['cabecas_de_chave'].strip():
            cabecas_input = request.form['cabecas_de_chave'].strip()
            cabecas_de_chave_nomes = [nome.strip() for nome in cabecas_input.split(',') 
                                      if nome.strip() and nome.strip() in nomes]
            
            # Validar número de cabeças de chave
            num_grupos = {
                '16j': 4, '20j': 5, '24j': 6, '28j': 7, '32j': 8
            }.get(modo, 7)
            
            if len(cabecas_de_chave_nomes) > num_grupos:
                error_msg = f"Número de cabeças de chave ({len(cabecas_de_chave_nomes)}) excede o número de grupos ({num_grupos})"
                current_app.logger.error(error_msg)
                session['erro_validacao'] = error_msg
                return redirect(url_for('main.novo_torneio'))
            
            log_action("seeds_selected", f"Cabeças de chave: {', '.join(cabecas_de_chave_nomes)}")

        grupos_nomes = criar_grupos(list(nomes), modo, cabecas_de_chave_nomes)
        for grupo_idx, grupo_nomes in enumerate(grupos_nomes):
            grupo = [session['jogadores'][nome] for nome in grupo_nomes]
            session['grupos'].append(grupo)
            confrontos_grupo = gerar_confrontos(grupo)
            session['confrontos'].append(confrontos_grupo)
            
            # Salvar confrontos no banco
            for confronto_idx, confronto in enumerate(confrontos_grupo):
                # Criando o confronto no banco
                novo_confronto = Confronto(
                    torneio_id=novo_torneio.id,
                    grupo_idx=grupo_idx,
                    confronto_idx=confronto_idx,
                    jogador_a1_id=session['jogadores'][confronto[0]['nome']]['id'],
                    jogador_a2_id=session['jogadores'][confronto[1]['nome']]['id'],
                    jogador_b1_id=session['jogadores'][confronto[2]['nome']]['id'],
                    jogador_b2_id=session['jogadores'][confronto[3]['nome']]['id']
                )
                db.session.add(novo_confronto)
                log_action("confronto_created", 
                          f"Confronto DB: G{grupo_idx+1}-C{confronto_idx+1} - "
                          f"{confronto[0]['nome']}&{confronto[1]['nome']} x "
                          f"{confronto[2]['nome']}&{confronto[3]['nome']}")
        
        db.session.commit()
        
        log_action("tournament_created", 
                  f"Torneio criado com sucesso - {len(grupos_nomes)} grupos")
        session.pop('erro_validacao', None)
        return redirect(url_for('main.novo_torneio'))
    
    except Exception as e:
        error_msg = f"Erro no sorteio: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        db.session.rollback()  # Importante: rollback no caso de erro
        return redirect(url_for('main.novo_torneio'))
    
@bp.route('/salvar_grupo/<int:grupo_idx>', methods=['POST'])
def salvar_grupo(grupo_idx):
    """Função para salvar os resultados de apenas um grupo especifico"""
    try:
        log_action("group_save_start", 
                  f"Salvando Grupo {grupo_idx + 1} - Dados: {dict(request.form)}") 
        
        # Inicializa valores salvos se necessário
        session.setdefault('valores_salvos', {})

        # Processa campos do formulário
        for key, value in request.form.items():
            if key.startswith(f'grupo_{grupo_idx}_'):
                session['valores_salvos'][key] = value
                if not value.isdigit() and value:
                    current_app.logger.warning(f"Valor inválido no campo {key}: {value}")

        # Reset estatísticas
        grupo_nomes = [j['nome'] for j in session['grupos'][grupo_idx]]
        for nome in grupo_nomes:
            session['jogadores'][nome].update({
                'vitorias': 0,
                'saldo_a_favor': 0,
                'saldo_contra': 0,
                'saldo_total': 0
            })
        
        # Verificar IDs dos jogadores no banco
        torneio_id = session.get('torneio_id')
        if not torneio_id:
            raise ValueError("ID do torneio não encontrado na sessão")
            
        # Verificar jogadores no banco
        with db.session.no_autoflush:
            for nome in grupo_nomes:
                jogador_id = session['jogadores'][nome]['id']
                db_jogador = Jogador.query.get(jogador_id)
                
                if not db_jogador:
                    log_action("jogador_not_found", f"Jogador não encontrado no banco: {nome} (ID: {jogador_id})")
                    # Tente recuperar por nome e torneio
                    db_jogador = Jogador.query.filter_by(nome=nome, torneio_id=torneio_id).first()
                    
                    if db_jogador:
                        # Atualizar ID na sessão
                        session['jogadores'][nome]['id'] = db_jogador.id
                        log_action("jogador_id_fixed", f"ID do jogador {nome} atualizado para {db_jogador.id}")
                    else:
                        # Se ainda não encontrar, criar um novo
                        # Primeiro encontrar ou criar o jogador permanente
                        jogador_permanente = JogadorPermanente.query.filter_by(nome=nome).first()
                        if not jogador_permanente:
                            jogador_permanente = JogadorPermanente(nome=nome)
                            db.session.add(jogador_permanente)
                            db.session.flush()
                        
                        # Criar novo jogador
                        novo_jogador = Jogador(
                            nome=nome, 
                            torneio_id=torneio_id,
                            jogador_permanente_id=jogador_permanente.id
                        )
                        db.session.add(novo_jogador)
                        db.session.flush()
                        session['jogadores'][nome]['id'] = novo_jogador.id
                        log_action("jogador_created", f"Novo jogador criado: {nome} (ID: {novo_jogador.id})")
            
            # Commit para garantir que todos os jogadores estejam no banco
            db.session.commit()
        
        # Processa cada confronto
        for confronto_idx, confronto in enumerate(session['confrontos'][grupo_idx]):
            campo_A = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaA_favor"
            campo_B = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaB_favor"

            try:
                saldoA = int(session['valores_salvos'].get(campo_A, 0)) if session['valores_salvos'].get(campo_A, '') else 0
                saldoB = int(session['valores_salvos'].get(campo_B, 0)) if session['valores_salvos'].get(campo_B, '') else 0
                
                # Atualiza estatísticas para cada jogador
                jogadores = {
                    'A': [session['jogadores'][confronto[0]['nome']], 
                         session['jogadores'][confronto[1]['nome']]],
                    'B': [session['jogadores'][confronto[2]['nome']], 
                         session['jogadores'][confronto[3]['nome']]]
                }

                for jogador in jogadores['A']:
                    jogador['saldo_a_favor'] += saldoA
                    jogador['saldo_contra'] += saldoB
                    if saldoA > saldoB:
                        jogador['vitorias'] += 1

                for jogador in jogadores['B']:
                    jogador['saldo_a_favor'] += saldoB
                    jogador['saldo_contra'] += saldoA
                    if saldoB > saldoA:
                        jogador['vitorias'] += 1

                # Atualiza o confronto no banco de dados
                torneio_id = session.get('torneio_id')
                confronto_db = Confronto.query.filter_by(
                    torneio_id=torneio_id, 
                    grupo_idx=grupo_idx, 
                    confronto_idx=confronto_idx
                ).first()
                
                if confronto_db:
                    # Se o confronto já existe, atualize os resultados
                    confronto_db.pontos_dupla_a = saldoA
                    confronto_db.pontos_dupla_b = saldoB
                    log_action("confronto_updated", 
                              f"Confronto DB atualizado: G{grupo_idx+1}-C{confronto_idx+1} - "
                              f"Placar: {saldoA} x {saldoB}")
                else:
                    # Se o confronto não existe (não deveria acontecer), crie-o
                    novo_confronto = Confronto(
                        torneio_id=torneio_id,
                        grupo_idx=grupo_idx,
                        confronto_idx=confronto_idx,
                        jogador_a1_id=session['jogadores'][confronto[0]['nome']]['id'],
                        jogador_a2_id=session['jogadores'][confronto[1]['nome']]['id'],
                        jogador_b1_id=session['jogadores'][confronto[2]['nome']]['id'],
                        jogador_b2_id=session['jogadores'][confronto[3]['nome']]['id'],
                        pontos_dupla_a=saldoA,
                        pontos_dupla_b=saldoB
                    )
                    db.session.add(novo_confronto)
                    log_action("confronto_created_late", 
                              f"Confronto DB criado tardiamente: G{grupo_idx+1}-C{confronto_idx+1}")
            
            except (KeyError, ValueError) as e:
                current_app.logger.error(f"Erro processando confronto {confronto_idx}: {str(e)}")
                raise
            
        # Atualiza e classifica o grupo
        for jogador in session['grupos'][grupo_idx]:
            jogador_ref = session['jogadores'][jogador['nome']]
            jogador.update({
                'vitorias': jogador_ref['vitorias'],
                'saldo_a_favor': jogador_ref['saldo_a_favor'],
                'saldo_contra': jogador_ref['saldo_contra'],
                'saldo_total': jogador_ref['saldo_a_favor'] - jogador_ref['saldo_contra']
            })

        session['grupos'][grupo_idx].sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
        session.modified = True

        # Primeiro commit para salvar as alterações nos confrontos
        db.session.commit()
        
        # Atualiza os jogadores no banco com os dados de posição
        for i, jogador_dados in enumerate(session['grupos'][grupo_idx]):
            nome = jogador_dados['nome']
            posicao = i + 1  # Posição no grupo (1-based)
            
            # Buscar jogador no banco
            jogador = Jogador.query.get(session['jogadores'][nome]['id'])
            if jogador:
                # Atualiza estatísticas e posição
                jogador.vitorias = jogador_dados['vitorias']
                jogador.saldo_a_favor = jogador_dados['saldo_a_favor']
                jogador.saldo_contra = jogador_dados['saldo_contra']
                jogador.saldo_total = jogador_dados['saldo_total']
                jogador.posicao_grupo = posicao
                jogador.grupo_idx = grupo_idx
                
                # Também atualizar na tabela de participação
                if jogador.jogador_permanente_id:
                    participacao = ParticipacaoTorneio.query.filter_by(
                        jogador_permanente_id=jogador.jogador_permanente_id,
                        torneio_id=torneio_id
                    ).first()
                    
                    if participacao:
                        participacao.vitorias = jogador_dados['vitorias']
                        participacao.saldo_a_favor = jogador_dados['saldo_a_favor']
                        participacao.saldo_contra = jogador_dados['saldo_contra']
                        participacao.saldo_total = jogador_dados['saldo_total']
                        participacao.posicao_grupo = posicao
                        participacao.grupo_idx = grupo_idx
                
                # Commit individual para garantir a persistência
                db.session.commit()
            else:
                current_app.logger.warning(f"Jogador não encontrado para atualização: {nome}")
        
        log_action("group_saved", 
                  f"Grupo {grupo_idx + 1} salvo - Resultados: {session['grupos'][grupo_idx]}")
        return redirect(url_for('main.novo_torneio'))
    
    except Exception as e:
        error_msg = f"Erro ao salvar Grupo {grupo_idx + 1}: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        db.session.rollback()
        return redirect(url_for('main.novo_torneio'))

@bp.route('/salvar_todos_grupos', methods=['POST'])
def salvar_todos_grupos():
    """Função para salvar resultados parciais ou de todos os grupos"""
    try:
        log_action("all_groups_save_start", "Salvando todos os grupos")
        
        # Inicializa valores salvos se necessário
        session.setdefault('valores_salvos', {})

        # Processa campos do formulário
        for key, value in request.form.items():
            session['valores_salvos'][key] = value
            if key.startswith('grupo_') and not value.isdigit() and value:
                current_app.logger.warning(f"Valor inválido no campo {key}: {value}")

        # Reset estatísticas para todos os jogadores
        for nome, jogador in session['jogadores'].items():
            jogador.update({
                'vitorias': 0,
                'saldo_a_favor': 0,
                'saldo_contra': 0,
                'saldo_total': 0
            })
        
        # Verificar se os jogadores existem no banco antes de processar confrontos
        torneio_id = session.get('torneio_id')
        if not torneio_id:
            raise ValueError("ID do torneio não encontrado na sessão")
            
        # Verificar jogadores no banco
        jogadores_db = {}
        for nome, jogador in session['jogadores'].items():
            db_jogador = Jogador.query.get(jogador['id'])
            if not db_jogador:
                log_action("jogador_not_found", f"Jogador não encontrado no banco: {nome} (ID: {jogador['id']})")
                # Tente recuperar por nome e torneio
                db_jogador = Jogador.query.filter_by(nome=nome, torneio_id=torneio_id).first()
                if db_jogador:
                    # Atualizar ID na sessão
                    jogador['id'] = db_jogador.id
                    log_action("jogador_id_fixed", f"ID do jogador {nome} atualizado para {db_jogador.id}")
                else:
                    # Se ainda não encontrar, criar um novo
                    # Primeiro encontrar ou criar o jogador permanente
                    jogador_permanente = JogadorPermanente.query.filter_by(nome=nome).first()
                    if not jogador_permanente:
                        jogador_permanente = JogadorPermanente(nome=nome)
                        db.session.add(jogador_permanente)
                        db.session.flush()
                    
                    # Criar novo jogador
                    novo_jogador = Jogador(
                        nome=nome, 
                        torneio_id=torneio_id,
                        jogador_permanente_id=jogador_permanente.id
                    )
                    db.session.add(novo_jogador)
                    db.session.flush()
                    jogador['id'] = novo_jogador.id
                    log_action("jogador_created", f"Novo jogador criado: {nome} (ID: {novo_jogador.id})")
            
            jogadores_db[nome] = db_jogador or Jogador.query.get(jogador['id'])
        
        # Commit para garantir que todos os jogadores estejam no banco
        db.session.commit()
        
        with db.session.no_autoflush:  # Evita problemas de autoflush
            # Processa cada grupo
            for grupo_idx in range(len(session['grupos'])):
                # Processa cada confronto do grupo
                for confronto_idx, confronto in enumerate(session['confrontos'][grupo_idx]):
                    campo_A = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaA_favor"
                    campo_B = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaB_favor"

                    try:
                        saldoA = int(session['valores_salvos'].get(campo_A, 0)) if session['valores_salvos'].get(campo_A, '') else 0
                        saldoB = int(session['valores_salvos'].get(campo_B, 0)) if session['valores_salvos'].get(campo_B, '') else 0
                        
                        # Atualiza estatísticas para cada jogador
                        jogadores = {
                            'A': [session['jogadores'][confronto[0]['nome']], 
                                  session['jogadores'][confronto[1]['nome']]],
                            'B': [session['jogadores'][confronto[2]['nome']], 
                                  session['jogadores'][confronto[3]['nome']]]
                        }

                        for jogador in jogadores['A']:
                            jogador['saldo_a_favor'] += saldoA
                            jogador['saldo_contra'] += saldoB
                            if saldoA > saldoB:
                                jogador['vitorias'] += 1

                        for jogador in jogadores['B']:
                            jogador['saldo_a_favor'] += saldoB
                            jogador['saldo_contra'] += saldoA
                            if saldoB > saldoA:
                                jogador['vitorias'] += 1

                        # Atualiza o confronto no banco de dados
                        # Verificar se existe e atualizar ou criar
                        confronto_db = Confronto.query.filter_by(
                            torneio_id=torneio_id, 
                            grupo_idx=grupo_idx, 
                            confronto_idx=confronto_idx
                        ).first()
                        
                        if confronto_db:
                            # Se o confronto já existe, apenas atualize os resultados
                            confronto_db.pontos_dupla_a = saldoA
                            confronto_db.pontos_dupla_b = saldoB
                            log_action("confronto_updated", 
                                      f"Confronto DB atualizado: G{grupo_idx+1}-C{confronto_idx+1} - "
                                      f"Placar: {saldoA} x {saldoB}")
                        else:
                            # Se o confronto não existe, crie-o
                            novo_confronto = Confronto(
                                torneio_id=torneio_id,
                                grupo_idx=grupo_idx,
                                confronto_idx=confronto_idx,
                                jogador_a1_id=session['jogadores'][confronto[0]['nome']]['id'],
                                jogador_a2_id=session['jogadores'][confronto[1]['nome']]['id'],
                                jogador_b1_id=session['jogadores'][confronto[2]['nome']]['id'],
                                jogador_b2_id=session['jogadores'][confronto[3]['nome']]['id'],
                                pontos_dupla_a=saldoA,
                                pontos_dupla_b=saldoB
                            )
                            db.session.add(novo_confronto)
                            log_action("confronto_created_late", 
                                      f"Confronto DB criado: G{grupo_idx+1}-C{confronto_idx+1}")
                    
                    except (KeyError, ValueError) as e:
                        current_app.logger.error(f"Erro processando confronto {confronto_idx} do grupo {grupo_idx}: {str(e)}")
                        continue  # Continue processando outros confrontos mesmo se um falhar
                
                # Atualiza e classifica o grupo
                for jogador in session['grupos'][grupo_idx]:
                    jogador_ref = session['jogadores'][jogador['nome']]
                    jogador.update({
                        'vitorias': jogador_ref['vitorias'],
                        'saldo_a_favor': jogador_ref['saldo_a_favor'],
                        'saldo_contra': jogador_ref['saldo_contra'],
                        'saldo_total': jogador_ref['saldo_a_favor'] - jogador_ref['saldo_contra']
                    })

                # Classifica o grupo
                session['grupos'][grupo_idx].sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
        
        session.modified = True

        # Commit para salvar as alterações nos confrontos
        db.session.commit()
        
        # Atualiza os jogadores no banco com os dados de posição
        for grupo_idx in range(len(session['grupos'])):
            for i, jogador_dados in enumerate(session['grupos'][grupo_idx]):
                nome = jogador_dados['nome']
                posicao = i + 1  # Posição no grupo (1-based)
                
                # Buscar jogador no banco
                jogador = Jogador.query.get(session['jogadores'][nome]['id'])
                if jogador:
                    # Atualiza estatísticas e posição
                    jogador.vitorias = jogador_dados['vitorias']
                    jogador.saldo_a_favor = jogador_dados['saldo_a_favor']
                    jogador.saldo_contra = jogador_dados['saldo_contra']
                    jogador.saldo_total = jogador_dados['saldo_total']
                    jogador.posicao_grupo = posicao
                    jogador.grupo_idx = grupo_idx
                    
                    # Atualizar também na tabela de participação
                    participacao = ParticipacaoTorneio.query.filter_by(
                        jogador_permanente_id=jogador.jogador_permanente_id,
                        torneio_id=torneio_id
                    ).first()
                    
                    if participacao:
                        participacao.vitorias = jogador_dados['vitorias']
                        participacao.saldo_a_favor = jogador_dados['saldo_a_favor']
                        participacao.saldo_contra = jogador_dados['saldo_contra']
                        participacao.saldo_total = jogador_dados['saldo_total']
                        participacao.posicao_grupo = posicao
                        participacao.grupo_idx = grupo_idx                  
                else:
                    log_action("jogador_not_found_for_update", 
                              f"Jogador não encontrado para atualização: {nome}")
        
        # Commit final
        db.session.commit()
        log_action("all_groups_saved", f"Todos os {len(session['grupos'])} grupos salvos com sucesso")
        return redirect(url_for('main.novo_torneio'))
    
    except Exception as e:
        error_msg = f"Erro ao salvar todos os grupos: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        db.session.rollback()
        return redirect(url_for('main.novo_torneio'))

def obter_confrontos_db(torneio_id):
    """Recupera os confrontos do banco de dados para um determinado torneio"""
    confrontos_db = {}
    try:
        # Busca todos os confrontos do torneio
        confrontos = Confronto.query.filter_by(torneio_id=torneio_id).all()
        
        # Organiza confrontos por grupo e índice
        for confronto in confrontos:
            grupo_idx = confronto.grupo_idx
            confronto_idx = confronto.confronto_idx
            
            if grupo_idx not in confrontos_db:
                confrontos_db[grupo_idx] = {}
            
            # Armazena os dados do confronto
            confrontos_db[grupo_idx][confronto_idx] = {
                'jogador_a1_id': confronto.jogador_a1_id,
                'jogador_a2_id': confronto.jogador_a2_id,
                'jogador_b1_id': confronto.jogador_b1_id,
                'jogador_b2_id': confronto.jogador_b2_id,
                'pontos_dupla_a': confronto.pontos_dupla_a,
                'pontos_dupla_b': confronto.pontos_dupla_b
            }
        
        log_action("confrontos_loaded", f"Carregados {len(confrontos)} confrontos do torneio {torneio_id}")
        return confrontos_db
    
    except Exception as e:
        log_action("confrontos_load_error", f"Erro ao carregar confrontos: {str(e)}")
        return {}

@bp.route('/carregar_torneio/<int:torneio_id>', methods=['GET'])
def carregar_torneio(torneio_id):
    """Função para carregar torneio"""
    try:
        # Recupera o torneio
        torneio = Torneio.query.get_or_404(torneio_id)
        
        # Recupera os jogadores do torneio
        jogadores = Jogador.query.filter_by(torneio_id=torneio_id).all()
        
        # Recupera os confrontos do torneio
        confrontos_db = obter_confrontos_db(torneio_id)
        
        # Popula a sessão com os dados
        session['torneio_id'] = torneio_id
        session['modo_torneio'] = torneio.modo  # Você precisa adicionar este campo ao modelo Torneio
        
        # Configura jogadores na sessão
        session['jogadores'] = {
            jogador.nome: {
                'nome': jogador.nome,
                'id': jogador.id,
                'vitorias': jogador.vitorias,
                'saldo_a_favor': jogador.saldo_a_favor,
                'saldo_contra': jogador.saldo_contra,
                'saldo_total': jogador.saldo_total
            } for jogador in jogadores
        }
        
        log_action("torneio_loaded", f"Torneio {torneio_id} carregado na sessão")
        return redirect(url_for('main.novo_torneio'))
        
    except Exception as e:
        error_msg = f"Erro ao carregar torneio: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        return redirect(url_for('main.home'))
    
@bp.route('/trocar_jogador', methods=['POST'])
def trocar_jogador():
    """Função para trocar um jogador com outro jogador de outro grupo aleatório"""
    try:
        # Obter dados da requisição
        data = request.get_json()
        jogador_id = data.get('jogador_id')
        grupo_atual_idx = int(data.get('grupo_atual'))
        
        # Verificar se o torneio existe na sessão
        torneio_id = session.get('torneio_id')
        if not torneio_id:
            return jsonify({'success': False, 'error': 'Torneio não encontrado na sessão'}), 400
        
        log_action("player_swap_start", f"Jogador ID: {jogador_id}, Grupo atual: {grupo_atual_idx}")
        
        # Verificar quantos grupos existem no torneio atual
        total_grupos = len(session.get('grupos', []))
        log_action("player_swap_debug", f"Total de grupos na sessão: {total_grupos}")
        
        if total_grupos <= 1:
            log_action("player_swap_error", "Não há grupos suficientes para fazer a troca")
            return jsonify({
                'success': False, 
                'error': 'É necessário ter pelo menos 2 grupos para fazer a troca'
            }), 400
        
        # Verificar se o jogador existe
        jogador = Jogador.query.get(jogador_id)
        if not jogador:
            log_action("player_swap_error", f"Jogador ID {jogador_id} não encontrado")
            return jsonify({'success': False, 'error': 'Jogador não encontrado'}), 400
        
        # Verificar se existem confrontos já registrados
        confrontos_existentes = Confronto.query.filter(
            Confronto.torneio_id == torneio_id,
            db.or_(
                Confronto.pontos_dupla_a != None, 
                Confronto.pontos_dupla_b != None
            )
        ).first()
        
        if confrontos_existentes:
            log_action("player_swap_error", "Confrontos já registrados impedem a troca")
            return jsonify({
                'success': False, 
                'error': 'Não é possível trocar jogadores após registrar resultados. Você precisa resetar os resultados primeiro.'
            }), 400
        
        # Escolher um grupo de destino diferente do atual
        # Vamos listar todos os índices de grupos e escolher um diferente
        grupos_disponiveis = list(range(total_grupos))
        
        # Remover o grupo atual das opções
        if grupo_atual_idx in grupos_disponiveis:
            grupos_disponiveis.remove(grupo_atual_idx)
        
        if not grupos_disponiveis:
            log_action("player_swap_error", "Não há outros grupos disponíveis")
            return jsonify({'success': False, 'error': 'Não há outros grupos disponíveis para troca'}), 400
        
        # Selecionar um grupo de destino aleatoriamente
        grupo_destino_idx = random.choice(grupos_disponiveis)
        
        log_action("player_swap_destination", f"Grupo destino: {grupo_destino_idx}")
        
        if grupo_destino_idx >= len(session['grupos']):
            log_action("player_swap_error", f"Índice de grupo destino inválido: {grupo_destino_idx}")
            return jsonify({'success': False, 'error': f'Índice de grupo destino inválido: {grupo_destino_idx}'}), 400
        
        # Obter todos os jogadores do grupo de destino da sessão
        jogadores_destino_sessao = session['grupos'][grupo_destino_idx]
        
        if not jogadores_destino_sessao:
            log_action("player_swap_error", f"Não há jogadores no grupo de destino {grupo_destino_idx}")
            return jsonify({'success': False, 'error': 'Não há jogadores no grupo de destino'}), 400
        
        # Selecionar um jogador aleatório do grupo de destino
        jogador_destino_sessao = random.choice(jogadores_destino_sessao)
        jogador_destino_id = jogador_destino_sessao['id']
        
        # Verificar se o jogador de destino existe no banco
        jogador_destino = Jogador.query.get(jogador_destino_id)
        if not jogador_destino:
            log_action("player_swap_error", f"Jogador destino ID {jogador_destino_id} não encontrado")
            return jsonify({'success': False, 'error': 'Jogador destino não encontrado'}), 400
        
        log_action("player_swap_target", f"Jogador destino: {jogador_destino.nome} (ID: {jogador_destino.id})")
        
        # Fazer a troca dos grupos no banco de dados
        temp_grupo_idx = jogador.grupo_idx
        jogador.grupo_idx = jogador_destino.grupo_idx
        jogador_destino.grupo_idx = temp_grupo_idx
        
        # Atualizar os confrontos na sessão
        # 1. Trocar os jogadores nos grupos
        jogador_atual_idx = None
        jogador_destino_idx = None
        
        # Encontrar posições dos jogadores nos grupos
        for i, j in enumerate(session['grupos'][grupo_atual_idx]):
            if int(j['id']) == int(jogador_id):
                jogador_atual_idx = i
                break
                
        for i, j in enumerate(session['grupos'][grupo_destino_idx]):
            if int(j['id']) == int(jogador_destino_id):
                jogador_destino_idx = i
                break
        
        if jogador_atual_idx is None or jogador_destino_idx is None:
            log_action("player_swap_error", "Não foi possível encontrar os jogadores nos grupos")
            return jsonify({'success': False, 'error': 'Não foi possível encontrar os jogadores nos grupos'}), 400
        
        # Fazer a troca
        temp = session['grupos'][grupo_atual_idx][jogador_atual_idx]
        session['grupos'][grupo_atual_idx][jogador_atual_idx] = session['grupos'][grupo_destino_idx][jogador_destino_idx]
        session['grupos'][grupo_destino_idx][jogador_destino_idx] = temp
        
        # 2. Atualizar os confrontos
        session['confrontos'] = []
        
        for grupo_idx, grupo in enumerate(session['grupos']):
            confrontos_grupo = gerar_confrontos(grupo)
            session['confrontos'].append(confrontos_grupo)
        
        # Remover os confrontos atuais do banco de dados
        Confronto.query.filter_by(torneio_id=torneio_id).delete()
        db.session.flush()
        
        # Recriar os confrontos no banco de dados
        for grupo_idx, grupo_confrontos in enumerate(session['confrontos']):
            for confronto_idx, confronto in enumerate(grupo_confrontos):
                novo_confronto = Confronto(
                    torneio_id=torneio_id,
                    grupo_idx=grupo_idx,
                    confronto_idx=confronto_idx,
                    jogador_a1_id=confronto[0]['id'],
                    jogador_a2_id=confronto[1]['id'],
                    jogador_b1_id=confronto[2]['id'],
                    jogador_b2_id=confronto[3]['id']
                )
                db.session.add(novo_confronto)
            
            log_action("confrontos_recreated", f"Confrontos recriados para o grupo {grupo_idx}")
        
        # Salvar alterações no banco
        db.session.commit()
        session.modified = True
        
        log_action("player_swap_success", 
                  f"Troca concluída: Jogador {jogador.nome} movido para grupo {grupo_destino_idx}, "
                  f"Jogador {jogador_destino.nome} movido para grupo {grupo_atual_idx}")
        
        return jsonify({
            'success': True, 
            'message': 'Jogadores trocados com sucesso',
            'novo_grupo': grupo_destino_idx,
            'jogador_trocado_nome': jogador_destino.nome
        })
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao trocar jogadores: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({'success': False, 'error': error_msg}), 500
    
@bp.route('/buscar_jogadores_disponiveis', methods=['GET'])
def buscar_jogadores_disponiveis():
    """Endpoint para buscar jogadores que não estão no torneio atual"""
    try:
        termo = request.args.get('termo', '')
        if len(termo) < 2:
            return jsonify([])
        
        torneio_id = session.get('torneio_id')
        if not torneio_id:
            return jsonify([])
        
        # Obter IDs dos jogadores que já estão no torneio atual
        jogadores_torneio = Jogador.query.filter_by(torneio_id=torneio_id).all()
        jogadores_permanentes_ids = [j.jogador_permanente_id for j in jogadores_torneio if j.jogador_permanente_id]
        
        # Buscar jogadores permanentes que contenham o termo e não estão no torneio atual
        jogadores = JogadorPermanente.query.filter(
            JogadorPermanente.nome.ilike(f'%{termo}%'),
            ~JogadorPermanente.id.in_(jogadores_permanentes_ids) if jogadores_permanentes_ids else True
        ).order_by(JogadorPermanente.nome).limit(10).all()
        
        # Formatando resultado
        resultados = [{'id': j.id, 'nome': j.nome} for j in jogadores]
        
        return jsonify(resultados)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar jogadores disponíveis: {str(e)}", exc_info=True)
        return jsonify([])

@bp.route('/substituir_jogador', methods=['POST'])
def substituir_jogador():
    """Função para substituir um jogador por outro jogador"""
    try:
        # Obter dados da requisição
        data = request.get_json()
        jogador_id = data.get('jogador_id')
        grupo_atual = int(data.get('grupo_atual'))
        jogador_existente = data.get('jogador_existente', False)
        novo_jogador_id = data.get('novo_jogador_id')
        novo_jogador_nome = data.get('novo_jogador_nome', '').strip()
        
        # Verificar se o torneio existe na sessão
        torneio_id = session.get('torneio_id')
        if not torneio_id:
            return jsonify({'success': False, 'error': 'Torneio não encontrado na sessão'}), 400
        
        log_action("player_substitution_start", 
                  f"Jogador ID: {jogador_id}, Grupo: {grupo_atual}, " 
                  f"Usando jogador existente: {jogador_existente}")
        
        # Verificar se o jogador a ser substituído existe
        jogador = Jogador.query.get(jogador_id)
        if not jogador:
            log_action("player_substitution_error", f"Jogador ID {jogador_id} não encontrado")
            return jsonify({'success': False, 'error': 'Jogador não encontrado'}), 400
        
        # Verificar se existem confrontos já registrados
        confrontos_existentes = Confronto.query.filter(
            Confronto.torneio_id == torneio_id,
            db.or_(
                Confronto.pontos_dupla_a != None, 
                Confronto.pontos_dupla_b != None
            )
        ).first()
        
        if confrontos_existentes:
            log_action("player_substitution_error", "Confrontos já registrados impedem a substituição")
            return jsonify({
                'success': False, 
                'error': 'Não é possível substituir jogadores após registrar resultados. Você precisa resetar os resultados primeiro.'
            }), 400
        
        # Obter ou criar o jogador permanente para substituição
        jogador_permanente_novo = None
        
        if jogador_existente and novo_jogador_id:
            # Usar jogador permanente existente
            jogador_permanente_novo = JogadorPermanente.query.get(novo_jogador_id)
            if not jogador_permanente_novo:
                log_action("player_substitution_error", f"Jogador permanente ID {novo_jogador_id} não encontrado")
                return jsonify({'success': False, 'error': 'Jogador permanente não encontrado'}), 400
        else:
            # Criar novo jogador permanente
            if not novo_jogador_nome:
                log_action("player_substitution_error", "Nome do novo jogador não fornecido")
                return jsonify({'success': False, 'error': 'Nome do novo jogador não fornecido'}), 400
            
            # Verificar se já existe um jogador com esse nome
            jogador_existente = JogadorPermanente.query.filter(
                JogadorPermanente.nome.ilike(novo_jogador_nome)
            ).first()
            
            if jogador_existente:
                jogador_permanente_novo = jogador_existente
                log_action("player_substitution_info", 
                          f"Usando jogador permanente existente com nome {novo_jogador_nome}")
            else:
                # Criar novo jogador permanente
                jogador_permanente_novo = JogadorPermanente(nome=novo_jogador_nome)
                db.session.add(jogador_permanente_novo)
                db.session.flush()
                log_action("player_substitution_info", 
                          f"Criado novo jogador permanente: {novo_jogador_nome} (ID: {jogador_permanente_novo.id})")
        
        # Verificar se o jogador já está no torneio
        jogador_ja_no_torneio = Jogador.query.filter_by(
            torneio_id=torneio_id,
            jogador_permanente_id=jogador_permanente_novo.id
        ).first()
        
        if jogador_ja_no_torneio:
            log_action("player_substitution_error", f"Jogador {jogador_permanente_novo.nome} já está no torneio")
            return jsonify({
                'success': False, 
                'error': f'O jogador {jogador_permanente_novo.nome} já está participando do torneio atual'
            }), 400
        
        # Atualizar o jogador no banco de dados
        nome_antigo = jogador.nome
        jogador.nome = jogador_permanente_novo.nome
        jogador.jogador_permanente_id = jogador_permanente_novo.id
        
        # Criar ou atualizar a participação no torneio
        participacao = ParticipacaoTorneio.query.filter_by(
            jogador_permanente_id=jogador_permanente_novo.id,
            torneio_id=torneio_id
        ).first()
        
        if not participacao:
            participacao = ParticipacaoTorneio(
                jogador_permanente_id=jogador_permanente_novo.id,
                torneio_id=torneio_id,
                grupo_idx=grupo_atual
            )
            db.session.add(participacao)
        
        # Encontrar o jogador na sessão e atualizá-lo
        for idx, j in enumerate(session['grupos'][grupo_atual]):
            if int(j['id']) == int(jogador_id):
                # Atualizar jogador na sessão
                j['nome'] = jogador_permanente_novo.nome
                break
        
        # Atualizar também no dicionário de jogadores
        session['jogadores'][jogador_permanente_novo.nome] = session['jogadores'].pop(nome_antigo)
        session['jogadores'][jogador_permanente_novo.nome]['nome'] = jogador_permanente_novo.nome
        
        # Atualizar confrontos na sessão
        for idx_grupo, grupo_confrontos in enumerate(session['confrontos']):
            for idx_confronto, confronto in enumerate(grupo_confrontos):
                for idx_jogador in range(4):
                    if confronto[idx_jogador]['nome'] == nome_antigo:
                        session['confrontos'][idx_grupo][idx_confronto][idx_jogador]['nome'] = jogador_permanente_novo.nome
        
        # Remover os confrontos atuais do banco de dados
        Confronto.query.filter_by(torneio_id=torneio_id).delete()
        db.session.flush()
        
        # Recriar os confrontos no banco de dados
        for grupo_idx, grupo_confrontos in enumerate(session['confrontos']):
            for confronto_idx, confronto in enumerate(grupo_confrontos):
                novo_confronto = Confronto(
                    torneio_id=torneio_id,
                    grupo_idx=grupo_idx,
                    confronto_idx=confronto_idx,
                    jogador_a1_id=session['jogadores'][confronto[0]['nome']]['id'],
                    jogador_a2_id=session['jogadores'][confronto[1]['nome']]['id'],
                    jogador_b1_id=session['jogadores'][confronto[2]['nome']]['id'],
                    jogador_b2_id=session['jogadores'][confronto[3]['nome']]['id']
                )
                db.session.add(novo_confronto)
            
            log_action("confrontos_recreated", f"Confrontos recriados para o grupo {grupo_idx}")
        
        # Salvar alterações no banco
        db.session.commit()
        session.modified = True
        
        log_action("player_substitution_success", 
                  f"Substituição concluída: Jogador {nome_antigo} substituído por {jogador_permanente_novo.nome}")
        
        return jsonify({
            'success': True, 
            'message': 'Jogador substituído com sucesso',
            'nome_antigo': nome_antigo,
            'novo_jogador_nome': jogador_permanente_novo.nome
        })
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao substituir jogador: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({'success': False, 'error': error_msg}), 500