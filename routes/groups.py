"""Funções para criação de grupos"""
import random
import re
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, session, current_app
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

def criar_grupos(jogadores, modo):
    """Divide os jogadores em grupos de 4 com logging"""
    random.shuffle(jogadores)
    num_groups = {
        '20j': (20, 5),
        '24j': (24, 6),
        '28j': (28, 7),
        '32j': (32, 8)
    }.get(modo, (28, 7))
    
    grupos = [jogadores[i:i+4] for i in range(0, num_groups[0], 4)]
    log_action("groups_created", f"Modo: {modo} - {num_groups[1]} grupos criados")
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
        # Verificar se já existem grupos sorteados
        if 'grupos' in session and session['grupos']:
            log_action("tournament_start_prevented", "Tentativa de novo sorteio com grupos existentes")
            session['erro_validacao'] = "Um sorteio já foi realizado. Para realizar um novo sorteio, cancele o torneio atual."
            return redirect(url_for('main.novo_torneio'))
            
        modo = request.form.get('modo_torneio', '28j')
        nome_torneio = request.form.get('nome_torneio', 'Torneio Sem Nome')
        log_action("tournament_start", f"Iniciando sorteio - Modo: {modo}")

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
            '20j': 20, '24j': 24, 
            '28j': 28, '32j': 32
        }.get(modo, 28)
        
        if len(nomes) != expected_players:
            error_msg = f"Jogadores incorretos! Esperado: {expected_players}, Recebido: {len(nomes)}"
            current_app.logger.error(error_msg)
            session['erro_validacao'] = error_msg
            return redirect(url_for('main.novo_torneio'))
        
        # Cria novo torneio
        novo_torneio = Torneio(nome=nome_torneio)
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
        
        grupos_nomes = criar_grupos(list(nomes), modo)
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