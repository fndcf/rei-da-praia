from flask import Blueprint, request, redirect, url_for, session, current_app
import random
import re
from datetime import datetime
from database.models import Jogador, Torneio, Confronto
from database.db import db


bp = Blueprint('groups', __name__)

def log_action(action, details):
    """Função auxiliar para padronizar logs"""
    current_app.logger.info(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{action.upper()} - {details}"
    )

# Mova suas funções auxiliares para cá
def criar_jogador(nome):
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
    try:
        modo = request.form.get('modo_torneio', '28j')
        nome_torneio = request.form.get('nome_torneio', 'Torneio Sem Nome')
        log_action("tournament_start", f"Iniciando sorteio - Modo: {modo}")

        # Verifica se há um torneio finalizado com mesmo nome
        torneio_existente = Torneio.query.filter_by(nome=nome_torneio).order_by(Torneio.id.desc()).first()
        if torneio_existente and torneio_existente.finalizado:
            session['erro_validacao'] = "Este torneio já foi finalizado. Crie um novo com outro nome."
            return redirect(url_for('main.home'))
        
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
        db.session.commit()
        
        # Cria jogadores vinculados ao torneio
        jogadores_dict = {}
        for nome in nomes:
            jogador = Jogador(nome=nome, torneio_id=novo_torneio.id)
            db.session.add(jogador)
            jogadores_dict[nome] = jogador
        db.session.commit()
        
        # Cria estrutura de dados
        session.update({
            'torneio_id': novo_torneio.id,
            'modo_torneio': modo,
            'jogadores': {
                nome: {
                    'nome': jogador.nome,
                    'id': jogador.id,  # Adicionamos o ID para referência
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
        return redirect(url_for('main.novo_torneio'))
    
@bp.route('/salvar_grupo/<int:grupo_idx>', methods=['POST'])
def salvar_grupo(grupo_idx):
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
        
        # Agora atualizamos posição dos jogadores com commits individuais
        for i, jogador_dados in enumerate(session['grupos'][grupo_idx]):
            nome = jogador_dados['nome']
            posicao = i + 1  # Posição no grupo (1-based)
            
            # Busca novamente o jogador para ter uma instância atualizada
            jogador = Jogador.query.filter_by(
                nome=nome, 
                torneio_id=session.get('torneio_id')
            ).first()
            
            if jogador:
                # Atualiza estatísticas e posição
                jogador.vitorias = jogador_dados['vitorias']
                jogador.saldo_a_favor = jogador_dados['saldo_a_favor']
                jogador.saldo_contra = jogador_dados['saldo_contra']
                jogador.saldo_total = jogador_dados['saldo_total']
                jogador.posicao_grupo = posicao
                jogador.grupo_idx = grupo_idx
                
                # Commit individual para garantir a persistência
                db.session.commit()
                
                # Log para debug
                log_action("jogador_position_updated", 
                          f"Jogador: {nome}, Grupo: {grupo_idx}, Posição: {posicao}")
        
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
                        # Caso o confronto não exista (não deveria acontecer), crie-o
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

        # Importantíssimo: Commit no banco para garantir persistência das alterações anteriores
        db.session.commit()
        
        # Atualiza o banco com os dados de posição
        # Fazemos isso APÓS o commit anterior para garantir que todas as alterações sejam persistidas
        for grupo_idx in range(len(session['grupos'])):
            # Atualiza as posições no banco de dados
            for i, jogador_dados in enumerate(session['grupos'][grupo_idx]):
                nome = jogador_dados['nome']
                posicao = i + 1  # Posição no grupo (1, 2, 3, 4)
                
                # Busca novamente o jogador do banco para ter certeza que estamos com a instância atualizada
                jogador = Jogador.query.filter_by(
                    nome=nome, 
                    torneio_id=session.get('torneio_id')
                ).first()
                
                if jogador:
                    # Registra informações de debug para verificar valores
                    current_app.logger.debug(
                        f"Atualizando posição: Jogador {jogador.nome} | "
                        f"Grupo {grupo_idx} | Posição {posicao}"
                    )
                    
                    # Garante que os valores sejam atualizados
                    jogador.vitorias = jogador_dados['vitorias']
                    jogador.saldo_a_favor = jogador_dados['saldo_a_favor']
                    jogador.saldo_contra = jogador_dados['saldo_contra']
                    jogador.saldo_total = jogador_dados['saldo_total']
                    jogador.posicao_grupo = posicao
                    jogador.grupo_idx = grupo_idx
                    
                    # Commit individual para cada jogador
                    db.session.commit()
                else:
                    current_app.logger.error(f"Jogador não encontrado: {nome}")
        
        log_action("all_groups_saved", f"Todos os {len(session['grupos'])} grupos salvos com sucesso")
        return redirect(url_for('main.novo_torneio'))
    
    except Exception as e:
        error_msg = f"Erro ao salvar todos os grupos: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        db.session.rollback()
        return redirect(url_for('main.novo_torneio'))

# Função auxiliar para obter confrontos do banco de dados
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

# Você pode adicionar ainda uma rota para recuperar dados de um torneio existente
@bp.route('/carregar_torneio/<int:torneio_id>', methods=['GET'])
def carregar_torneio(torneio_id):
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
        
        # TODO: Reconstruir grupos e confrontos da sessão a partir dos dados do banco
        # Isso exigiria recuperar a configuração de grupos do torneio
        
        log_action("torneio_loaded", f"Torneio {torneio_id} carregado na sessão")
        return redirect(url_for('main.novo_torneio'))
        
    except Exception as e:
        error_msg = f"Erro ao carregar torneio: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        return redirect(url_for('main.home'))