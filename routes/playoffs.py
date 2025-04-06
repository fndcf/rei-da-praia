from flask import Blueprint, render_template, session, url_for, redirect, request, flash

bp = Blueprint('playoffs', __name__)

@bp.route('/fase_eliminatoria')
def fase_eliminatoria():
    modo = session.get('modo_torneio', request.form.get('modo', '28j'))
    if 'grupos' not in session:
        return redirect(url_for('main.index'))
    primeiros = sorted([grupo[0] for grupo in session['grupos'] if len(grupo) > 0], 
                      key=lambda x: (-x['vitorias'], -x['saldo_total']))
    segundos = sorted([grupo[1] for grupo in session['grupos'] if len(grupo) > 1],
                     key=lambda x: (-x['vitorias'], -x['saldo_total'])) 
    
    # Inicializa o histórico de jogos
    historico_jogos = {}

    # Configuração baseada no modo
    if modo == '20j':
        # 20 jogadores: 1 jogo nas quartas, 2 nas semis, final é o jogo 4
        confrontos = [
            {'timeA': [segundos[1], segundos[2]], 'timeB': [segundos[3], segundos[4]], 'jogo': 1}
        ]
        num_jogos_quartas = 1
        num_jogos_semis = 2
        jogo_final = 4
        inicio_semis = 2

    elif modo == '24j':
        # 24 jogadores: 2 jogos nas quartas, 2 nas semis, final é o jogo 5
        confrontos = [
            {'timeA': [segundos[0], segundos[1]], 'timeB': [segundos[2], segundos[3]], 'jogo': 1},
            {'timeA': [primeiros[4], primeiros[5]], 'timeB': [segundos[4], segundos[5]], 'jogo': 2}
        ]
        num_jogos_quartas = 2
        num_jogos_semis = 2
        jogo_final = 5
        inicio_semis = 3

    elif modo == '28j':
        # 28 jogadores: 3 jogos nas quartas, 2 nas semis, final é o jogo 6
        confrontos = [
            {'timeA': [primeiros[6], segundos[0]], 'timeB': [segundos[1], segundos[2]], 'jogo': 1},
            {'timeA': [primeiros[2], primeiros[3]], 'timeB': [segundos[5], segundos[6]], 'jogo': 2},
            {'timeA': [primeiros[4], primeiros[5]], 'timeB': [segundos[3], segundos[4]], 'jogo': 3}
        ]
        num_jogos_quartas = 3
        num_jogos_semis = 2
        jogo_final = 6
        inicio_semis = 4

    else:
        # 32 jogadores: 4 jogos nas quartas, 2 nas semis, final é o jogo 7
        confrontos = [
            {'timeA': [primeiros[0], primeiros[1]], 'timeB': [segundos[6], segundos[7]], 'jogo': 1},
            {'timeA': [primeiros[2], primeiros[3]], 'timeB': [segundos[4], segundos[5]], 'jogo': 2},
            {'timeA': [primeiros[4], primeiros[5]], 'timeB': [segundos[2], segundos[3]], 'jogo': 3},
            {'timeA': [primeiros[6], primeiros[7]], 'timeB': [segundos[0], segundos[1]], 'jogo': 4}
        ]
        num_jogos_quartas = 4
        num_jogos_semis = 2
        jogo_final = 7
        inicio_semis = 5

    # Adiciona quartas ao histórico
    for jogo in range(1, num_jogos_quartas + 1):
        jogo_key = f'eliminatoria_jogo{jogo}'
        if jogo_key in session:
            historico_jogos[f'Quartas - Jogo {jogo}'] = {
                'timeA': session[jogo_key]['timeA'],
                'timeB': session[jogo_key]['timeB'],
                'timeA_nomes': [jogador['nome'] for jogador in confrontos[jogo-1]['timeA']],
                'timeB_nomes': [jogador['nome'] for jogador in confrontos[jogo-1]['timeB']]
            }

    # Verifica resultados para semi-finais
    semi_finais = []
    if all(f'eliminatoria_jogo{i}' in session for i in range(1, num_jogos_quartas + 1)):
        if modo == '20j':
            vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
            
            semi_finais = [
                {'timeA': [primeiros[0], primeiros[1]], 'timeB': confrontos[0][vencedor_jogo1], 'jogo': 2},
                {'timeA': [primeiros[2], primeiros[3]], 'timeB': [primeiros[4], segundos[0]], 'jogo': 3}
            ]
        elif modo == '24j':
            vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
            vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
            
            semi_finais = [
                {'timeA': [primeiros[0], primeiros[1]], 'timeB': confrontos[0][vencedor_jogo1], 'jogo': 3},
                {'timeA': [primeiros[2], primeiros[3]], 'timeB': confrontos[1][vencedor_jogo2], 'jogo': 4}
            ]
        elif modo == '28j':
            vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
            vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
            vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
            
            semi_finais = [
                {'timeA': [primeiros[0], primeiros[1]], 'timeB': confrontos[0][vencedor_jogo1], 'jogo': 4},
                {'timeA': confrontos[1][vencedor_jogo2], 'timeB': confrontos[2][vencedor_jogo3], 'jogo': 5}
            ]

        else:
            vencedor_jogo1 = 'timeA' if session['eliminatoria_jogo1']['timeA'] > session['eliminatoria_jogo1']['timeB'] else 'timeB'
            vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
            vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
            vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
            
            semi_finais = [
                {'timeA': confrontos[0][vencedor_jogo1], 'timeB': confrontos[1][vencedor_jogo2], 'jogo': 5},
                {'timeA': confrontos[2][vencedor_jogo3], 'timeB': confrontos[3][vencedor_jogo4], 'jogo': 6}
            ]

        # Adiciona semi-finais ao histórico
        for jogo in range(inicio_semis, inicio_semis + num_jogos_semis):
            jogo_key = f'eliminatoria_jogo{jogo}'
            if jogo_key in session:
                historico_jogos[f'Semi-Final - Jogo {jogo}'] = {
                    'timeA': session[jogo_key]['timeA'],
                    'timeB': session[jogo_key]['timeB'],
                    'timeA_nomes': [jogador['nome'] for jogador in semi_finais[jogo-inicio_semis]['timeA']],
                    'timeB_nomes': [jogador['nome'] for jogador in semi_finais[jogo-inicio_semis]['timeB']]
                }

    # Verifica resultados para final
    final = None
    if all(f'eliminatoria_jogo{i}' in session for i in range(inicio_semis, inicio_semis + num_jogos_semis)):
        if modo == '20j':
            vencedor_jogo2 = 'timeA' if session['eliminatoria_jogo2']['timeA'] > session['eliminatoria_jogo2']['timeB'] else 'timeB'
            vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
            
            final = {
                'timeA': semi_finais[0][vencedor_jogo2],
                'timeB': semi_finais[1][vencedor_jogo3],
                'jogo': jogo_final
            }
        elif modo == '24j':
            vencedor_jogo3 = 'timeA' if session['eliminatoria_jogo3']['timeA'] > session['eliminatoria_jogo3']['timeB'] else 'timeB'
            vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
            
            final = {
                'timeA': semi_finais[0][vencedor_jogo3],
                'timeB': semi_finais[1][vencedor_jogo4],
                'jogo': jogo_final
            }
        elif modo == '28j':
            vencedor_jogo4 = 'timeA' if session['eliminatoria_jogo4']['timeA'] > session['eliminatoria_jogo4']['timeB'] else 'timeB'
            vencedor_jogo5 = 'timeA' if session['eliminatoria_jogo5']['timeA'] > session['eliminatoria_jogo5']['timeB'] else 'timeB'
            
            final = {
                'timeA': semi_finais[0][vencedor_jogo4],
                'timeB': semi_finais[1][vencedor_jogo5],
                'jogo': jogo_final
            }
        else:
            vencedor_jogo5 = 'timeA' if session['eliminatoria_jogo5']['timeA'] > session['eliminatoria_jogo5']['timeB'] else 'timeB'
            vencedor_jogo6 = 'timeA' if session['eliminatoria_jogo6']['timeA'] > session['eliminatoria_jogo6']['timeB'] else 'timeB'
            
            final = {
                'timeA': semi_finais[0][vencedor_jogo5],
                'timeB': semi_finais[1][vencedor_jogo6],
                'jogo': jogo_final
            }

        # Adiciona final ao histórico
        if f'eliminatoria_jogo{jogo_final}' in session:
            historico_jogos['Final'] = {
                'timeA': session[f'eliminatoria_jogo{jogo_final}']['timeA'],
                'timeB': session[f'eliminatoria_jogo{jogo_final}']['timeB'],
                'timeA_nomes': [jogador['nome'] for jogador in final['timeA']],
                'timeB_nomes': [jogador['nome'] for jogador in final['timeB']]
            }

    return render_template('fase_eliminatoria.html',
                         primeiros=primeiros,
                         segundos=segundos,
                         confrontos=confrontos,
                         semi_finais=semi_finais,
                         final=final,
                         historico_jogos=historico_jogos,
                         modo_torneio=modo)

@bp.route('/salvar_eliminatorias', methods=['POST'])
def salvar_eliminatorias():
    modo = session.get('modo_torneio', request.form.get('modo', '28j'))
    if modo == '28j':
        num_jogos_quartas = 3
    elif modo == '20j':
        num_jogos_quartas = 1
    elif modo == '24j':
        num_jogos_quartas = 2
    else:
        num_jogos_quartas = 4
    try:
        # Processa os resultados
        for jogo in range(1, num_jogos_quartas + 1):
            campo_timeA = f"jogo_{jogo}_timeA"
            campo_timeB = f"jogo_{jogo}_timeB"
            
            # Aqui você pode salvar os resultados na sessão
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': int(request.form.get(campo_timeA, 0)),
                'timeB': int(request.form.get(campo_timeB, 0))
            }
        
        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        print(f"Erro: {str(e)}")
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
@bp.route('/salvar_semi_finais', methods=['POST'])
def salvar_semi_finais():
    modo = request.form.get('modo')    
    if modo == '28j':
        inicio_semis = 4
    elif modo == '20j':
        inicio_semis = 2
    elif modo == '24j':
        inicio_semis = 3
    else:
        inicio_semis = 5
    try:
        for jogo in [inicio_semis, inicio_semis + 1]:
            campo_timeA = f"jogo_{jogo}_timeA"
            campo_timeB = f"jogo_{jogo}_timeB"
            
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': int(request.form.get(campo_timeA, 0)),
                'timeB': int(request.form.get(campo_timeB, 0))
            }
        
        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        print(f"Erro: {str(e)}")
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
@bp.route('/gerar_final', methods=['POST'])
def gerar_final():
    modo = request.form.get('modo')
        
    if modo == '28j':
        inicio_semis = 4
    elif modo == '20j':
        inicio_semis = 2
    elif modo == '24j':
        inicio_semis = 3
    else:
        inicio_semis = 5
    try:
        # Salva os resultados das semi-finais antes de gerar a final
        for jogo in [inicio_semis, inicio_semis + 1]:
            campo_timeA = f"jogo_{jogo}_timeA"
            campo_timeB = f"jogo_{jogo}_timeB"
            
            session[f'eliminatoria_jogo{jogo}'] = {
                'timeA': int(request.form.get(campo_timeA, 0)),
                'timeB': int(request.form.get(campo_timeB, 0))
            }
        
        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    
    except Exception as e:
        print(f"Erro ao gerar final: {str(e)}")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/salvar_final', methods=['POST'])
def salvar_final():
    modo = request.form.get('modo')
    if modo == '28j':
        jogo_final = 6
    elif modo == '20j':
        jogo_final = 4
    elif modo == '24j':
        jogo_final = 5
    else:
        jogo_final = 7
    try:
        session[f'eliminatoria_jogo{jogo_final}'] = {
            'timeA': int(request.form.get(f'jogo_{jogo_final}_timeA', 0)),  # Corrigido
            'timeB': int(request.form.get(f'jogo_{jogo_final}_timeB', 0))   # Corrigido
        }
        session.modified = True
        return redirect(url_for('playoffs.fase_eliminatoria'))
    except Exception as e:
        print(f"Erro: {str(e)}")
        return redirect(url_for('playoffs.fase_eliminatoria'))

@bp.route('/resetar_eliminatorias')
def resetar_eliminatorias():
    try:
        # Remove todos os dados da fase eliminatória
        for i in range(1, 8):  # Jogos de 1 a 7
            session.pop(f'eliminatoria_jogo{i}', None)
        
        # Adicione esta linha para garantir que a sessão seja salva
        session.modified = True
        
        return {'success': True}, 200
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500