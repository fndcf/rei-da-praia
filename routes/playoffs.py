from flask import Blueprint, render_template, session, url_for, redirect, request, flash, current_app
from datetime import datetime
import logging

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
            return redirect(url_for('main.index'))

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
            return redirect(url_for('main.index'))

        # Validação de jogadores suficientes
        req = config['required_players']
        if len(primeiros) < req['primeiros'] or len(segundos) < req['segundos']:
            error_msg = (f"Jogadores insuficientes para modo {modo}. "
                       f"Necessário: {req['primeiros']}P/{req['segundos']}S. "
                       f"Encontrado: {len(primeiros)}P/{len(segundos)}S")
            current_app.logger.error(error_msg)
            flash("Erro: Configuração de torneio incompleta", "error")
            return redirect(url_for('main.index'))

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
        return redirect(url_for('main.index'))

@bp.route('/salvar_eliminatorias', methods=['POST'])
def salvar_eliminatorias():
    try:
        modo = session.get('modo_torneio', '28j')
        log_playoff_action("save_quarterfinals_start")

        num_jogos = {'20j':1, '24j':2, '28j':3, '32j':4}.get(modo, 3)
        
        for jogo in range(1, num_jogos + 1):
            timeA = int(request.form.get(f'jogo_{jogo}_timeA', 0))
            timeB = int(request.form.get(f'jogo_{jogo}_timeB', 0))
            
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': timeA,
                'timeB': timeB
            }
            current_app.logger.info(f"Quartas Jogo {jogo} salvo: {timeA}x{timeB}")

        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.error(
            f"Erro ao salvar quartas: {str(e)}",
            exc_info=True
        )
        flash("Erro ao salvar resultados das quartas", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/salvar_semi_finais', methods=['POST'])
def salvar_semi_finais():
    try:
        modo = request.form.get('modo', '28j')
        inicio_semis = {'20j':2, '24j':3, '28j':4, '32j':5}.get(modo, 4)
        log_playoff_action("save_semifinals_start", f"Jogos: {inicio_semis}-{inicio_semis+1}")

        for jogo in [inicio_semis, inicio_semis + 1]:
            timeA = int(request.form.get(f'jogo_{jogo}_timeA', 0))
            timeB = int(request.form.get(f'jogo_{jogo}_timeB', 0))
            
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': timeA,
                'timeB': timeB
            }
            current_app.logger.debug(f"Semi-final Jogo {jogo}: {timeA}x{timeB}")

        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.error(
            f"Erro ao salvar semi-finais: {str(e)}",
            exc_info=True
        )
        flash("Erro ao salvar semi-finais", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/salvar_final', methods=['POST'])
def salvar_final():
    try:
        modo = request.form.get('modo', '28j')
        jogo_final = {'20j':4, '24j':5, '28j':6, '32j':7}.get(modo, 6)
        
        # DEBUG: Log todo o formulário recebido
        current_app.logger.debug(f"Form data recebido: {dict(request.form)}")
        
        timeA = request.form.get(f'jogo_{jogo_final}_timeA')
        timeB = request.form.get(f'jogo_{jogo_final}_timeB')
        
        # Validação rigorosa
        if not timeA or not timeB:
            raise ValueError("Placar incompleto")
        
        timeA = int(timeA)
        timeB = int(timeB)
        
        # Valida valores positivos
        if timeA < 0 or timeB < 0:
            raise ValueError("Placar não pode ser negativo")

        session[f'eliminatoria_jogo{jogo_final}'] = {
            'timeA': timeA,
            'timeB': timeB
        }

        current_app.logger.info(
            f"FINAL SALVA | {timeA}x{timeB} | "
            f"Campeão: {'TimeA' if timeA > timeB else 'TimeB'} | "
            f"Modo: {modo} | "
            f"Jogo: {jogo_final}"
        )

        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except ValueError as e:
        current_app.logger.error(
            f"Erro ao salvar final: {str(e)} | "
            f"Formulário: {dict(request.form)}",
            exc_info=True
        )
        flash(f"Erro: {str(e)}", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        current_app.logger.critical(
            f"Falha crítica ao salvar final: {str(e)} | "
            f"Formulário: {dict(request.form)}",
            exc_info=True
        )
        flash("Erro interno ao salvar a final", "error")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/resetar_eliminatorias')
def resetar_eliminatorias():
    try:
        log_playoff_action("reset_start")
        
        for i in range(1, 8):
            session.pop(f'eliminatoria_jogo{i}', None)
        
        session.modified = True
        current_app.logger.info("Fase eliminatória resetada com sucesso")
        return {'success': True}, 200
    
    except Exception as e:
        current_app.logger.error(
            f"Falha ao resetar eliminatórias: {str(e)}",
            exc_info=True
        )
        return {'success': False, 'error': str(e)}, 500