from flask import Blueprint, render_template, session, url_for, redirect, request, flash, current_app
from datetime import datetime
import logging
from database.models import Jogador, Torneio, Confronto, ConfrontoEliminatoria
from database.ranking import RankingManager
from database.db import db

bp = Blueprint('playoffs', __name__)

def log_playoff_action(action, details=""):
    """Log padronizado para ações da fase eliminatória"""
    current_app.logger.info(
        f"[PLAYOFF] {action.upper()} | "
        f"Modo: {session.get('modo_torneio', 'unknown')} | "
        f"Details: {details}"
    )

def get_jogador_safe(lista, idx, default=None):
    """Acesso seguro a lista de jogadores com fallback"""
    if idx < len(lista) and lista[idx]:
        return lista[idx]
    current_app.logger.warning(f"Índice {idx} inválido para lista de {len(lista)} jogadores")
    return default or {'nome': 'Jogador Fantasma', 'vitorias': 0, 'saldo_total': 0}

@bp.route('/fase_eliminatoria')
def fase_eliminatoria():
    try:
        modo = session.get('modo_torneio', '28j')
        log_playoff_action("phase_accessed", f"Modo: {modo}")

        # Verificação inicial crítica
        if 'grupos' not in session or not session['grupos']:
            current_app.logger.error("Nenhum grupo encontrado na sessão!")
            flash("Erro: Torneio não foi gerado corretamente", "error")
            return redirect(url_for('main.novo_torneio'))

        # Classificação segura
        primeiros = []
        segundos = []
        for grupo in session['grupos']:
            if len(grupo) > 0:
                primeiros.append(grupo[0])
            if len(grupo) > 1:
                segundos.append(grupo[1])

        primeiros.sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
        segundos.sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))

        current_app.logger.debug(
            f"Classificados - Primeiros: {[p['nome'] for p in primeiros[:3]]}... | "
            f"Segundos: {[s['nome'] for s in segundos[:3]]}..."
        )

        # Configuração centralizada para todos os modos
        config = {
            '20j': {
                'quartas': [
                    {'timeA': [get_jogador_safe(segundos, 1), get_jogador_safe(segundos, 2)],
                     'timeB': [get_jogador_safe(segundos, 3), get_jogador_safe(segundos, 4)], 
                     'jogo': 1}
                ],
                'required_players': {'primeiros': 5, 'segundos': 5},
                'final_jogo': 4
            },
            '24j': {
                'quartas': [
                    {'timeA': [get_jogador_safe(segundos, 0), get_jogador_safe(segundos, 1)],
                     'timeB': [get_jogador_safe(segundos, 2), get_jogador_safe(segundos, 3)], 
                     'jogo': 1},
                    {'timeA': [get_jogador_safe(primeiros, 4), get_jogador_safe(primeiros, 5)],
                     'timeB': [get_jogador_safe(segundos, 4), get_jogador_safe(segundos, 5)], 
                     'jogo': 2}
                ],
                'required_players': {'primeiros': 6, 'segundos': 6},
                'final_jogo': 5
            },
            '28j': {
                'quartas': [
                    {'timeA': [get_jogador_safe(primeiros, 6), get_jogador_safe(segundos, 0)],
                     'timeB': [get_jogador_safe(segundos, 1), get_jogador_safe(segundos, 2)], 
                     'jogo': 1},
                    {'timeA': [get_jogador_safe(primeiros, 2), get_jogador_safe(primeiros, 3)],
                     'timeB': [get_jogador_safe(segundos, 5), get_jogador_safe(segundos, 6)], 
                     'jogo': 2},
                    {'timeA': [get_jogador_safe(primeiros, 4), get_jogador_safe(primeiros, 5)],
                     'timeB': [get_jogador_safe(segundos, 3), get_jogador_safe(segundos, 4)], 
                     'jogo': 3}
                ],
                'required_players': {'primeiros': 7, 'segundos': 7},
                'final_jogo': 6
            },
            '32j': {
                'quartas': [
                    {'timeA': [get_jogador_safe(primeiros, 0), get_jogador_safe(primeiros, 1)],
                     'timeB': [get_jogador_safe(segundos, 6), get_jogador_safe(segundos, 7)], 
                     'jogo': 1},
                    {'timeA': [get_jogador_safe(primeiros, 2), get_jogador_safe(primeiros, 3)],
                     'timeB': [get_jogador_safe(segundos, 4), get_jogador_safe(segundos, 5)], 
                     'jogo': 2},
                    {'timeA': [get_jogador_safe(primeiros, 4), get_jogador_safe(primeiros, 5)],
                     'timeB': [get_jogador_safe(segundos, 2), get_jogador_safe(segundos, 3)], 
                     'jogo': 3},
                    {'timeA': [get_jogador_safe(primeiros, 6), get_jogador_safe(primeiros, 7)],
                     'timeB': [get_jogador_safe(segundos, 0), get_jogador_safe(segundos, 1)], 
                     'jogo': 4}
                ],
                'required_players': {'primeiros': 8, 'segundos': 8},
                'final_jogo': 7
            }
        }.get(modo)

        if not config:
            current_app.logger.error(f"Modo de torneio inválido: {modo}")
            flash("Modo de torneio inválido", "error")
            return redirect(url_for('main.novo_torneio'))

        # Validação de jogadores suficientes
        req = config['required_players']
        if len(primeiros) < req['primeiros'] or len(segundos) < req['segundos']:
            error_msg = (f"Jogadores insuficientes para modo {modo}. "
                       f"Necessário: {req['primeiros']}P/{req['segundos']}S. "
                       f"Encontrado: {len(primeiros)}P/{len(segundos)}S")
            current_app.logger.error(error_msg)
            flash("Erro: Configuração de torneio incompleta", "error")
            return redirect(url_for('main.novo_torneio'))

        # Geração de confrontos
        confrontos = config['quartas']
        historico_jogos = {}
        semi_finais = []
        final = None

        # Processa histórico das quartas
        for jogo in confrontos:
            jogo_key = f'eliminatoria_jogo{jogo["jogo"]}'
            if jogo_key in session:
                historico_jogos[f'Quartas - Jogo {jogo["jogo"]}'] = {
                    'timeA': session[jogo_key]['timeA'],
                    'timeB': session[jogo_key]['timeB'],
                    'timeA_nomes': [j['nome'] for j in jogo['timeA']],
                    'timeB_nomes': [j['nome'] for j in jogo['timeB']]
                }

        # Geração das semi-finais (se todas quartas estiverem salvas)
        if all(f'eliminatoria_jogo{j["jogo"]}' in session for j in confrontos):
            if modo == '20j':
                vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
                
                semi_finais = [
                    {
                        'timeA': [get_jogador_safe(primeiros, 0), get_jogador_safe(primeiros, 1)],
                        'timeB': confrontos[0][vencedor_jogo1],
                        'jogo': 2
                    },
                    {
                        'timeA': [get_jogador_safe(primeiros, 2), get_jogador_safe(primeiros, 3)],
                        'timeB': [get_jogador_safe(primeiros, 4), get_jogador_safe(segundos, 0)],
                        'jogo': 3
                    }
                ]

            elif modo == '24j':
                vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
                vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
                
                semi_finais = [
                    {
                        'timeA': [get_jogador_safe(primeiros, 0), get_jogador_safe(primeiros, 1)],
                        'timeB': confrontos[0][vencedor_jogo1],
                        'jogo': 3
                    },
                    {
                        'timeA': [get_jogador_safe(primeiros, 2), get_jogador_safe(primeiros, 3)],
                        'timeB': confrontos[1][vencedor_jogo2],
                        'jogo': 4
                    }
                ]

            elif modo == '28j':
                vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
                vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
                vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
                
                semi_finais = [
                    {
                        'timeA': [get_jogador_safe(primeiros, 0), get_jogador_safe(primeiros, 1)],
                        'timeB': confrontos[0][vencedor_jogo1],
                        'jogo': 4
                    },
                    {
                        'timeA': confrontos[1][vencedor_jogo2],
                        'timeB': confrontos[2][vencedor_jogo3],
                        'jogo': 5
                    }
                ]

            elif modo == '32j':
                vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
                vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
                vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
                vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
                
                semi_finais = [
                    {
                        'timeA': confrontos[0][vencedor_jogo1],
                        'timeB': confrontos[1][vencedor_jogo2],
                        'jogo': 5
                    },
                    {
                        'timeA': confrontos[2][vencedor_jogo3],
                        'timeB': confrontos[3][vencedor_jogo4],
                        'jogo': 6
                    }
                ]

            current_app.logger.debug(f"Semi-finais geradas: {len(semi_finais)} jogos")

            # Processa histórico das semi-finais
            for jogo in semi_finais:
                jogo_key = f'eliminatoria_jogo{jogo["jogo"]}'
                if jogo_key in session:
                    historico_jogos[f'Semi-Final - Jogo {jogo["jogo"]}'] = {
                        'timeA': session[jogo_key]['timeA'],
                        'timeB': session[jogo_key]['timeB'],
                        'timeA_nomes': [j['nome'] for j in jogo['timeA']],
                        'timeB_nomes': [j['nome'] for j in jogo['timeB']]
                    }

            # Geração da final (se todas semi-finais estiverem salvas)
            if all(f'eliminatoria_jogo{j["jogo"]}' in session for j in semi_finais):
                final_jogo = config['final_jogo']
                
                if modo == '20j':
                    vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
                    vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
                    
                    final = {
                        'timeA': semi_finais[0][vencedor_jogo2],
                        'timeB': semi_finais[1][vencedor_jogo3],
                        'jogo': final_jogo
                    }

                elif modo == '24j':
                    vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
                    vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
                    
                    final = {
                        'timeA': semi_finais[0][vencedor_jogo3],
                        'timeB': semi_finais[1][vencedor_jogo4],
                        'jogo': final_jogo
                    }

                elif modo == '28j':
                    vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
                    vencedor_jogo5 = 'timeA' if session['eliminatoria_jogo5']['timeA'] > session['eliminatoria_jogo5']['timeB'] else 'timeB'
                    
                    final = {
                        'timeA': semi_finais[0][vencedor_jogo4],
                        'timeB': semi_finais[1][vencedor_jogo5],
                        'jogo': final_jogo
                    }

                elif modo == '32j':
                    vencedor_jogo5 = 'timeA' if session['eliminatoria_jogo5']['timeA'] > session['eliminatoria_jogo5']['timeB'] else 'timeB'
                    vencedor_jogo6 = 'timeA' if session['eliminatoria_jogo6']['timeA'] > session['eliminatoria_jogo6']['timeB'] else 'timeB'
                    
                    final = {
                        'timeA': semi_finais[0][vencedor_jogo5],
                        'timeB': semi_finais[1][vencedor_jogo6],
                        'jogo': final_jogo
                    }

                current_app.logger.info(f"Final gerada - Jogo {final_jogo}")

                # Processa histórico da final
                if f'eliminatoria_jogo{final_jogo}' in session:
                    historico_jogos['Final'] = {
                        'timeA': session[f'eliminatoria_jogo{final_jogo}']['timeA'],
                        'timeB': session[f'eliminatoria_jogo{final_jogo}']['timeB'],
                        'timeA_nomes': [j['nome'] for j in final['timeA']],
                        'timeB_nomes': [j['nome'] for j in final['timeB']]
                    }

        return render_template('fase_eliminatoria.html',
                            primeiros=primeiros,
                            segundos=segundos,
                            confrontos=confrontos,
                            semi_finais=semi_finais,
                            final=final,
                            historico_jogos=historico_jogos,
                            modo_torneio=modo)

    except Exception as e:
        current_app.logger.critical(
            f"Falha na fase eliminatória: {str(e)}",
            exc_info=True
        )
        flash("Erro crítico ao gerar a fase eliminatória", "error")
        return redirect(url_for('main.novo_torneio'))

@bp.route('/salvar_eliminatorias', methods=['POST'])
def salvar_eliminatorias():
    try:
        modo = session.get('modo_torneio', '28j')
        torneio_id = session.get('torneio_id')
        log_playoff_action("save_quarterfinals_start")

        num_jogos = {'20j':1, '24j':2, '28j':3, '32j':4}.get(modo, 3)
        
        for jogo in range(1, num_jogos + 1):
            timeA = int(request.form.get(f'jogo_{jogo}_timeA', 0))
            timeB = int(request.form.get(f'jogo_{jogo}_timeB', 0))
            
            # Salvar na sessão (como já estava fazendo)
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': timeA,
                'timeB': timeB
            }
            
            # Pegar os nomes dos jogadores do formulário
            timeA_jogador1 = request.form.get(f'timeA_jogador1_{jogo}')
            timeA_jogador2 = request.form.get(f'timeA_jogador2_{jogo}')
            timeB_jogador1 = request.form.get(f'timeB_jogador1_{jogo}')
            timeB_jogador2 = request.form.get(f'timeB_jogador2_{jogo}')
            
            if torneio_id and all([timeA_jogador1, timeA_jogador2, timeB_jogador1, timeB_jogador2]):
                # Verificar se já existe este confronto no banco
                confronto_db = ConfrontoEliminatoria.query.filter_by(
                    torneio_id=torneio_id,
                    fase='quartas',
                    jogo_numero=jogo
                ).first()
                
                # Buscar IDs dos jogadores
                jogador_a1 = Jogador.query.filter_by(nome=timeA_jogador1, torneio_id=torneio_id).first()
                jogador_a2 = Jogador.query.filter_by(nome=timeA_jogador2, torneio_id=torneio_id).first()
                jogador_b1 = Jogador.query.filter_by(nome=timeB_jogador1, torneio_id=torneio_id).first()
                jogador_b2 = Jogador.query.filter_by(nome=timeB_jogador2, torneio_id=torneio_id).first()
                
                if all([jogador_a1, jogador_a2, jogador_b1, jogador_b2]):
                    if confronto_db:
                        # Atualizar confronto existente
                        confronto_db.pontos_dupla_a = timeA
                        confronto_db.pontos_dupla_b = timeB
                        confronto_db.atualizado_em = datetime.now()
                    else:
                        # Criar novo confronto
                        confronto_db = ConfrontoEliminatoria(
                            torneio_id=torneio_id,
                            fase='quartas',
                            jogo_numero=jogo,
                            jogador_a1_id=jogador_a1.id,
                            jogador_a2_id=jogador_a2.id,
                            jogador_b1_id=jogador_b1.id,
                            jogador_b2_id=jogador_b2.id,
                            pontos_dupla_a=timeA,
                            pontos_dupla_b=timeB
                        )
                        db.session.add(confronto_db)
                    
                    db.session.commit()
                    current_app.logger.info(f"Quartas Jogo {jogo} salvo no DB: {timeA}x{timeB}")
                else:
                    current_app.logger.warning(f"Não foi possível encontrar todos os jogadores para o confronto {jogo}")
            
            current_app.logger.info(f"Quartas Jogo {jogo} salvo na sessão: {timeA}x{timeB}")

        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.error(
            f"Erro ao salvar quartas: {str(e)}",
            exc_info=True
        )
        db.session.rollback()
        flash("Erro ao salvar resultados das quartas", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/salvar_semi_finais', methods=['POST'])
def salvar_semi_finais():
    try:
        modo = request.form.get('modo', '28j')
        torneio_id = session.get('torneio_id')
        inicio_semis = {'20j':2, '24j':3, '28j':4, '32j':5}.get(modo, 4)
        log_playoff_action("save_semifinals_start", f"Jogos: {inicio_semis}-{inicio_semis+1}")

        for jogo in [inicio_semis, inicio_semis + 1]:
            timeA = int(request.form.get(f'jogo_{jogo}_timeA', 0))
            timeB = int(request.form.get(f'jogo_{jogo}_timeB', 0))
            
            # Salvar na sessão
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': timeA,
                'timeB': timeB
            }
            
            # Pegar os nomes dos jogadores do formulário
            timeA_jogador1 = request.form.get(f'timeA_jogador1_{jogo}')
            timeA_jogador2 = request.form.get(f'timeA_jogador2_{jogo}')
            timeB_jogador1 = request.form.get(f'timeB_jogador1_{jogo}')
            timeB_jogador2 = request.form.get(f'timeB_jogador2_{jogo}')
            
            if torneio_id and all([timeA_jogador1, timeA_jogador2, timeB_jogador1, timeB_jogador2]):
                # Verificar se já existe este confronto no banco
                confronto_db = ConfrontoEliminatoria.query.filter_by(
                    torneio_id=torneio_id,
                    fase='semi',
                    jogo_numero=jogo
                ).first()
                
                # Buscar IDs dos jogadores
                jogador_a1 = Jogador.query.filter_by(nome=timeA_jogador1, torneio_id=torneio_id).first()
                jogador_a2 = Jogador.query.filter_by(nome=timeA_jogador2, torneio_id=torneio_id).first()
                jogador_b1 = Jogador.query.filter_by(nome=timeB_jogador1, torneio_id=torneio_id).first()
                jogador_b2 = Jogador.query.filter_by(nome=timeB_jogador2, torneio_id=torneio_id).first()
                
                if all([jogador_a1, jogador_a2, jogador_b1, jogador_b2]):
                    if confronto_db:
                        # Atualizar confronto existente
                        confronto_db.pontos_dupla_a = timeA
                        confronto_db.pontos_dupla_b = timeB
                        confronto_db.atualizado_em = datetime.now()
                    else:
                        # Criar novo confronto
                        confronto_db = ConfrontoEliminatoria(
                            torneio_id=torneio_id,
                            fase='semi',
                            jogo_numero=jogo,
                            jogador_a1_id=jogador_a1.id,
                            jogador_a2_id=jogador_a2.id,
                            jogador_b1_id=jogador_b1.id,
                            jogador_b2_id=jogador_b2.id,
                            pontos_dupla_a=timeA,
                            pontos_dupla_b=timeB
                        )
                        db.session.add(confronto_db)
                    
                    db.session.commit()
                    current_app.logger.debug(f"Semi-final Jogo {jogo} salvo no DB: {timeA}x{timeB}")
                else:
                    current_app.logger.warning(f"Não foi possível encontrar todos os jogadores para o confronto {jogo}")
            
            current_app.logger.debug(f"Semi-final Jogo {jogo} salvo na sessão: {timeA}x{timeB}")

        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.error(
            f"Erro ao salvar semi-finais: {str(e)}",
            exc_info=True
        )
        db.session.rollback()
        flash("Erro ao salvar semi-finais", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/salvar_final', methods=['POST'])
def salvar_final():
    try:
        modo = request.form.get('modo', '28j')
        torneio_id = session.get('torneio_id')
        jogo_final = {'20j':4, '24j':5, '28j':6, '32j':7}.get(modo, 6)

        # Obter os nomes dos jogadores do formulário
        timeA_jogador1 = request.form.get('timeA_jogador1', 'N/A')
        timeA_jogador2 = request.form.get('timeA_jogador2', 'N/A')
        timeB_jogador1 = request.form.get('timeB_jogador1', 'N/A')
        timeB_jogador2 = request.form.get('timeB_jogador2', 'N/A')

        # Armazenar as duplas na sessão
        session['final_dupla_timeA'] = [
            {'nome': timeA_jogador1},
            {'nome': timeA_jogador2}
        ]
        session['final_dupla_timeB'] = [
            {'nome': timeB_jogador1},
            {'nome': timeB_jogador2}
        ]
        
        timeA = int(request.form.get(f'jogo_{jogo_final}_timeA', 0))
        timeB = int(request.form.get(f'jogo_{jogo_final}_timeB', 0))
        
        # Armazena o placar na sessão
        session[f'eliminatoria_jogo{jogo_final}'] = {
            'timeA': timeA,
            'timeB': timeB
        }
        
        # Determina os campeões
        vencedor = 'timeA' if timeA > timeB else 'timeB'
        session['campea'] = session[f'final_dupla_{vencedor}']
        
        # Salvar no banco de dados
        if torneio_id:
            # Verificar se já existe este confronto no banco
            confronto_db = ConfrontoEliminatoria.query.filter_by(
                torneio_id=torneio_id,
                fase='final',
                jogo_numero=jogo_final
            ).first()
            
            # Obter IDs dos jogadores
            # Precisamos encontrar os IDs no dicionário de jogadores
            timeA_ids = [
                session['jogadores'].get(timeA_jogador1, {}).get('id', None),
                session['jogadores'].get(timeA_jogador2, {}).get('id', None)
            ]
            timeB_ids = [
                session['jogadores'].get(timeB_jogador1, {}).get('id', None),
                session['jogadores'].get(timeB_jogador2, {}).get('id', None)
            ]
            
            # Verificar se todos os IDs foram encontrados
            if all(timeA_ids) and all(timeB_ids):
                if confronto_db:
                    # Atualizar confronto existente
                    confronto_db.pontos_dupla_a = timeA
                    confronto_db.pontos_dupla_b = timeB
                    confronto_db.atualizado_em = datetime.now()
                else:
                    # Criar novo confronto
                    confronto_db = ConfrontoEliminatoria(
                        torneio_id=torneio_id,
                        fase='final',
                        jogo_numero=jogo_final,
                        jogador_a1_id=timeA_ids[0],
                        jogador_a2_id=timeA_ids[1],
                        jogador_b1_id=timeB_ids[0],
                        jogador_b2_id=timeB_ids[1],
                        pontos_dupla_a=timeA,
                        pontos_dupla_b=timeB
                    )
                    db.session.add(confronto_db)
                
                db.session.commit()
                current_app.logger.info(f"Final Jogo {jogo_final} salvo no DB: {timeA}x{timeB}")
            else:
                current_app.logger.warning("Não foi possível encontrar todos os IDs dos jogadores para salvar a final")
        
        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.error(f"Erro ao salvar final: {str(e)}")
        db.session.rollback()
        flash("Erro ao salvar a final", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/finalizar_torneio')
def finalizar_torneio():
    try:
        modo = session.get('modo_torneio', '28j')
        torneio_id = session.get('torneio_id')
        jogo_final = {'20j':4, '24j':5, '28j':6, '32j':7}.get(modo, 6)
        
        if f'eliminatoria_jogo{jogo_final}' not in session:
            flash("A final ainda não foi disputada!", "error")
            return redirect(url_for('playoffs.fase_eliminatoria'))
        
        final_data = session[f'eliminatoria_jogo{jogo_final}']
        
        # Determinar vencedor
        if final_data['timeA'] > final_data['timeB']:
            campeoes = session.get('final_dupla_timeA', [{'nome': 'N/A'}, {'nome': 'N/A'}])
            vice_campeoes = session.get('final_dupla_timeB', [{'nome': 'N/A'}, {'nome': 'N/A'}])
        else:
            campeoes = session.get('final_dupla_timeB', [{'nome': 'N/A'}, {'nome': 'N/A'}])
            vice_campeoes = session.get('final_dupla_timeA', [{'nome': 'N/A'}, {'nome': 'N/A'}])
        
        # Salvar na sessão para a tela de campeões
        session['campeoes_finais'] = {
            'campeoes': campeoes,
            'vice_campeoes': vice_campeoes,
            'placar': f"{final_data['timeA']}x{final_data['timeB']}"
        }
        
        # Atualizar o status 'finalizado' no banco de dados
        if torneio_id:
            torneio = Torneio.query.get(torneio_id)
            if torneio:
                torneio.finalizado = True
                db.session.commit()
                current_app.logger.info(f"Torneio {torneio_id} marcado como finalizado no banco de dados")
                
                # Calcular a pontuação dos jogadores neste torneio
                success = RankingManager.calcular_pontuacao_torneio(torneio_id)
                if success:
                    current_app.logger.info(f"Pontuação do torneio {torneio_id} calculada com sucesso")
                    flash("Pontuação do ranking calculada com sucesso!", "success")
                else:
                    current_app.logger.warning(f"Erro ao calcular pontuação do torneio {torneio_id}")
                    flash("Erro ao calcular pontuação do ranking", "warning")
        
        return redirect(url_for('playoffs.campeoes'))
    
    except Exception as e:
        current_app.logger.error(f"Erro ao finalizar torneio: {str(e)}")
        flash("Erro ao finalizar o torneio", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
@bp.route('/campeoes')
def campeoes():
    try:
        dados = session.get('campeoes_finais')
        if not dados:
            flash("Nenhum torneio finalizado encontrado!", "error")
            return redirect(url_for('main.novo_torneio'))
        
        return render_template('campeoes.html',
                            campeoes=dados['campeoes'],
                            vice_campeoes=dados['vice_campeoes'],
                            placar=dados['placar'],
                            modo_torneio=session.get('modo_torneio', '28j'),
                            data=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    except Exception as e:
        current_app.logger.error(f"Erro na tela de campeões: {str(e)}")
        flash("Erro ao exibir os campeões", "error")
        return redirect(url_for('main.novo_torneio'))
    
# Adicione esta rota no seu blueprint playoffs
@bp.route('/home_page')
def home_page():
    session.clear()
    return redirect(url_for('main.home'))

def obter_confrontos_eliminatorias_db(torneio_id):
    """Recupera os confrontos de eliminatórias do banco de dados para um determinado torneio"""
    confrontos_db = {}
    try:
        # Busca todos os confrontos eliminatórios do torneio
        confrontos = ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).all()
        
        # Organiza confrontos por fase e número do jogo
        for confronto in confrontos:
            fase = confronto.fase
            jogo_numero = confronto.jogo_numero
            
            if fase not in confrontos_db:
                confrontos_db[fase] = {}
            
            # Armazena os dados do confronto
            confrontos_db[fase][jogo_numero] = {
                'jogador_a1_id': confronto.jogador_a1_id,
                'jogador_a2_id': confronto.jogador_a2_id,
                'jogador_b1_id': confronto.jogador_b1_id,
                'jogador_b2_id': confronto.jogador_b2_id,
                'pontos_dupla_a': confronto.pontos_dupla_a,
                'pontos_dupla_b': confronto.pontos_dupla_b
            }
        
        log_playoff_action("confrontos_eliminatorias_loaded", f"Carregados {len(confrontos)} confrontos do torneio {torneio_id}")
        return confrontos_db
    
    except Exception as e:
        log_playoff_action("confrontos_eliminatorias_load_error", f"Erro ao carregar confrontos: {str(e)}")
        return {}