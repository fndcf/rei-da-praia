from flask import Blueprint, request, redirect, url_for, session, current_app
import random
import re
from datetime import datetime
from database.models import Jogador, Torneio
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
            return redirect('/')
        
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
            return redirect('/')
        
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
        for grupo_nomes in grupos_nomes:
            grupo = [session['jogadores'][nome] for nome in grupo_nomes]
            session['grupos'].append(grupo)
            session['confrontos'].append(gerar_confrontos(grupo))
        
        log_action("tournament_created", 
                  f"Torneio criado com sucesso - {len(grupos_nomes)} grupos")
        session.pop('erro_validacao', None)
        return redirect('/')
    
    except Exception as e:
        error_msg = f"Erro no sorteio: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        return redirect('/')
    
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
                if not value.isdigit():
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
                saldoA = int(session['valores_salvos'].get(campo_A, 0))
                saldoB = int(session['valores_salvos'].get(campo_B, 0))
                
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

        # Atualiza o banco com os dados salvos
        for nome, dados in session['jogadores'].items():
            dados['saldo_total'] = dados['saldo_a_favor'] - dados['saldo_contra']
            jogador = Jogador.query.filter_by(nome=nome).first()
            if jogador:
                jogador.vitorias = dados['vitorias']
                jogador.saldo_a_favor = dados['saldo_a_favor']
                jogador.saldo_contra = dados['saldo_contra']
                jogador.saldo_total = dados['saldo_total']
        db.session.commit()
        
        log_action("group_saved", 
                  f"Grupo {grupo_idx + 1} salvo - Resultados: {session['grupos'][grupo_idx]}")
        return redirect(url_for('main.index'))
    
    except Exception as e:
        error_msg = f"Erro ao salvar Grupo {grupo_idx + 1}: {str(e)}"
        current_app.logger.error(error_msg, exc_info=True)
        session['erro_validacao'] = error_msg
        return redirect(url_for('main.index'))
