from flask import Flask, render_template, request, redirect, session, url_for
from dotenv import load_dotenv
import random
import re
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

def criar_jogador(nome):
    """Cria um jogador com estrutura completa"""
    return {
        'nome': nome,
        'vitorias': 0,
        'saldo_a_favor': 0,
        'saldo_contra': 0,
        'saldo_total': 0
    }

def criar_grupos(jogadores):
    """Divide os jogadores em grupos de 4"""
    random.shuffle(jogadores)
    return [jogadores[i:i+4] for i in range(0, len(jogadores), 4)]

def gerar_confrontos(grupo):
    """Gera os 3 confrontos do grupo"""
    return [
        (grupo[0], grupo[1], grupo[2], grupo[3]),  # J1+J2 vs J3+J4
        (grupo[0], grupo[2], grupo[1], grupo[3]),  # J1+J3 vs J2+J4
        (grupo[0], grupo[3], grupo[1], grupo[2])   # J1+J4 vs J2+J3
    ]

@app.before_request
def init_session():
    """Garante que todas as estruturas existam na sessão"""
    session.setdefault('jogadores', {})
    session.setdefault('grupos', [])
    session.setdefault('confrontos', [])

@app.route('/')
def index():
    # Inicializa valores_salvos vazio se não existir
    valores_salvos = session.get('valores_salvos', {})
    
    # Garante estrutura completa para todos os jogadores
    for jogador in session.get('jogadores', {}).values():
        jogador.setdefault('vitorias', 0)
        jogador.setdefault('saldo_a_favor', 0)
        jogador.setdefault('saldo_contra', 0)
        jogador.setdefault('saldo_total', jogador.get('saldo_a_favor', 0) - jogador.get('saldo_contra', 0))

    # DEBUG: Mostrar dados ao carregar a página
    if 'grupos' in session:
        print("\nDADOS NA ROTA /:")
        for i, grupo in enumerate(session['grupos']):
            print(f"Grupo {i}:")
            for j in grupo:
                print(f"  {j['nome']}: V={j['vitorias']} ST={j['saldo_total']}")
        
    return render_template('index.html',
                         grupos=session.get('grupos', []),
                         confrontos=session.get('confrontos', []),
                         valores_salvos=session.get('valores_salvos', {}))

@app.route('/sorteio', methods=['POST'])
def sorteio():
    try:
        nomes = [nome.strip() for nome in request.form['jogadores'].split(',') if nome.strip() and re.match(r'^[a-zA-ZÀ-ú0-9\s,]+$', nome.strip())]
        
        # Validação rigorosa
        if len(nomes) < 28:
            session['erro_validacao'] = f"Faltam jogadores! (Atual: {len(nomes)}, Necessário: 28)"
        elif len(nomes) > 28:
            session['erro_validacao'] = f"Jogadores excedentes! (Atual: {len(nomes)}, Máximo: 28)"
        else:
            # Só executa o sorteio se tiver 28 jogadores
            session['jogadores'] = {nome: criar_jogador(nome) for nome in nomes}
            grupos_nomes = criar_grupos(nomes)
            session['grupos'] = []
            session['confrontos'] = []
            
            for grupo_nomes in grupos_nomes:
                grupo = [session['jogadores'][nome] for nome in grupo_nomes]
                session['grupos'].append(grupo)
                session['confrontos'].append(gerar_confrontos(grupo))
            
            session.pop('erro_validacao', None)
            return redirect('/')
        
        return redirect('/')
    
    except Exception as e:
        session['erro_validacao'] = f"Erro no formato dos dados: {str(e)}"
        return redirect('/')

@app.route('/salvar_grupo/<int:grupo_idx>', methods=['POST'])
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
        
        # Debug crítico
        print(f"\n=== GRUPO {grupo_idx} ATUALIZADO ===")
        for j in session['grupos'][grupo_idx]:
            print(f"{j['nome']}: V={j['vitorias']} SF={j['saldo_a_favor']} SC={j['saldo_contra']} ST={j['saldo_total']}")
        
        session.modified = True
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"ERRO: {str(e)}")
        session['erro_validacao'] = f"Erro no Grupo {grupo_idx+1}: {str(e)}"
        return redirect(url_for('index'))
    
# Adicione esta nova rota
@app.route('/fase_eliminatoria')
def fase_eliminatoria():
    # Verifica se os grupos existem na sessão
    if 'grupos' not in session or not session['grupos']:
        return redirect(url_for('index'))
    
    # Coleta os primeiros e segundos colocados
    primeiros_colocados = []
    segundos_colocados = []
    
    for grupo in session['grupos']:
        if len(grupo) >= 1:
            primeiros_colocados.append(grupo[0])
        if len(grupo) >= 2:
            segundos_colocados.append(grupo[1])
    
    # Ordena os colocados pelos mesmos critérios
    primeiros_colocados.sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
    segundos_colocados.sort(key=lambda x: (-x['vitorias'], -x['saldo_total']))
    
    return render_template('fase_eliminatoria.html',
                         primeiros=primeiros_colocados,
                         segundos=segundos_colocados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)