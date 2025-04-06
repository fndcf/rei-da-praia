from flask import Blueprint, request, redirect, url_for, session, jsonify
import random
import re

bp = Blueprint('groups', __name__)

# Mova suas funções auxiliares para cá
def criar_jogador(nome):
    return {
        'nome': nome,
        'vitorias': 0,
        'saldo_a_favor': 0,
        'saldo_contra': 0,
        'saldo_total': 0
    }

def criar_grupos(jogadores, modo):
    """Divide os jogadores em grupos de 4"""
    random.shuffle(jogadores)
    
    if modo == '24j':
        return [jogadores[i:i+4] for i in range(0, 24, 4)]  # 6 grupos
    elif modo == '28j':
        return [jogadores[i:i+4] for i in range(0, 28, 4)]  # 7 grupos
    else:  # 32j
        return [jogadores[i:i+4] for i in range(0, 32, 4)]  # 8 grupos

    
def gerar_confrontos(grupo):
    """Gera os 3 confrontos do grupo"""
    return [
        (grupo[0], grupo[1], grupo[2], grupo[3]),  # J1+J2 vs J3+J4
        (grupo[0], grupo[2], grupo[1], grupo[3]),  # J1+J3 vs J2+J4
        (grupo[0], grupo[3], grupo[1], grupo[2])   # J1+J4 vs J2+J3
    ]

@bp.route('/sorteio', methods=['POST'])
def sorteio():
    try:
        modo = request.form.get('modo_torneio', '28j')
        nomes = [nome.strip() for nome in request.form['jogadores'].split(',') if nome.strip() and re.match(r'^[a-zA-ZÀ-ú0-9\s,]+$', nome.strip())]   
        
        # Validação baseada no modo selecionado
        if modo == '24j':
            esperado = 24
        elif modo == '28j':
            esperado = 28
        elif modo == '32j':
            esperado = 32
        else:
            session['erro_validacao'] = f"Modo de torneio inválido: {modo}"
            return redirect('/')
        if len(nomes) != esperado:
            session['erro_validacao'] = f"Jogadores incorretos! (Atual: {len(nomes)}, Esperado: {esperado})"
            return redirect('/')
        
        session['modo_torneio'] = modo
        session['jogadores'] = {nome: criar_jogador(nome) for nome in nomes}
        grupos_nomes = criar_grupos(nomes, modo)
        session['grupos'] = []
        session['confrontos'] = []
        
        for grupo_nomes in grupos_nomes:
            grupo = [session['jogadores'][nome] for nome in grupo_nomes]
            session['grupos'].append(grupo)
            session['confrontos'].append(gerar_confrontos(grupo))
        
        session.pop('erro_validacao', None)
        return redirect('/')
    
    except Exception as e:
        session['erro_validacao'] = f"Erro no formato dos dados: {str(e)}"
        return redirect('/')
    
@bp.route('/salvar_grupo/<int:grupo_idx>', methods=['POST'])
def salvar_grupo(grupo_idx):
    try:
        # 1. Garante que os valores_salvos está inicializado
        if 'valores_salvos' not in session:
            session['valores_salvos'] = {}

        # 2. Processa TODOS os campos do formulário
        for key, value in request.form.items():
            if key.startswith(f'grupo_{grupo_idx}_'):
                session['valores_salvos'][key] = value

        # 3. Zera apenas os jogadores do grupo atual
        grupo_nomes = [j['nome'] for j in session['grupos'][grupo_idx]]
        for nome in grupo_nomes:
            session['jogadores'][nome].update({
                'vitorias': 0,
                'saldo_a_favor': 0,
                'saldo_contra': 0,
                'saldo_total': 0
            })

        # 4. Processa cada confronto do grupo
        for confronto_idx, confronto in enumerate(session['confrontos'][grupo_idx]):
            j1 = session['jogadores'][confronto[0]['nome']]
            j2 = session['jogadores'][confronto[1]['nome']]
            j3 = session['jogadores'][confronto[2]['nome']]
            j4 = session['jogadores'][confronto[3]['nome']]
            
            campo_A = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaA_favor"
            campo_B = f"grupo_{grupo_idx}_confronto_{confronto_idx}_duplaB_favor"
            
            saldoA = int(session['valores_salvos'].get(campo_A, 0))
            saldoB = int(session['valores_salvos'].get(campo_B, 0))
            
            # Atualiza estatísticas
            for jogador in [j1, j2]:
                jogador['saldo_a_favor'] += saldoA
                jogador['saldo_contra'] += saldoB
                if saldoA > saldoB:
                    jogador['vitorias'] += 1
            
            for jogador in [j3, j4]:
                jogador['saldo_a_favor'] += saldoB
                jogador['saldo_contra'] += saldoA
                if saldoB > saldoA:
                    jogador['vitorias'] += 1

        # 5. Atualiza referências no grupo
        for jogador in session['grupos'][grupo_idx]:
            jogador_ref = session['jogadores'][jogador['nome']]
            jogador.update({
                'vitorias': jogador_ref['vitorias'],
                'saldo_a_favor': jogador_ref['saldo_a_favor'],
                'saldo_contra': jogador_ref['saldo_contra'],
                'saldo_total': jogador_ref['saldo_a_favor'] - jogador_ref['saldo_contra']
            })

        # 6. Classifica o grupo
        session['grupos'][grupo_idx].sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))        
        session.modified = True
        return redirect(url_for('main.index'))
    
    except Exception as e:
        print(f"ERRO: {str(e)}")
        session['erro_validacao'] = f"Erro no Grupo {grupo_idx+1}: {str(e)}"
        return redirect(url_for('main.index'))
