"""Classes e funções para o Ranking dos jogadores"""
import logging
from sqlalchemy import text
from database.db import db
from database.models import Jogador, Torneio, ConfrontoEliminatoria


logger = logging.getLogger(__name__)

class RankingManager:
    """Classe para gerenciar o sistema de pontuação e ranking dos jogadores"""
    
    # Pontuação para cada fase (não cumulativa)
    PONTOS = {
        'quartas': 30,
        'semi': 50,
        'vice': 75,
        'campeao': 125
    }
    
    @staticmethod
    def atualizar_pontuacao_jogador(jogador_id, pontos):
        """Atualiza a pontuação do jogador"""
        try:
            jogador = Jogador.query.get(jogador_id)
            if jogador:
                jogador.pontuacao = pontos
                db.session.commit()
                logger.info(f"Pontuação do jogador {jogador.nome} atualizada: {pontos} pontos")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar pontuação do jogador {jogador_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def calcular_pontuacao_torneio(torneio_id):
        """Calcula a pontuação dos jogadores em um torneio específico"""
        try:
            # Verifica se o torneio está finalizado
            torneio = Torneio.query.get(torneio_id)
            if not torneio or not torneio.finalizado:
                logger.warning(f"Torneio {torneio_id} não está finalizado ou não existe")
                return False
            
            # Buscar todos os jogadores do torneio e resetar suas pontuações
            jogadores = Jogador.query.filter_by(torneio_id=torneio_id).all()
            for jogador in jogadores:
                jogador.pontuacao = 0
            db.session.commit()
            
            # Criar um mapeamento de jogadores para suas pontuações máximas
            pontuacoes_jogadores = {}
            
            # Buscar confrontos da fase eliminatória
            confrontos = ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).all()
            
            # Organizar por fase
            por_fase = {'quartas': [], 'semi': [], 'final': None}
            for confronto in confrontos:
                if confronto.fase == 'final':
                    por_fase['final'] = confronto
                else:
                    por_fase[confronto.fase].append(confronto)
            
            # Processar quartas de final (30 pontos)
            for confronto in por_fase['quartas']:
                jogadores_ids = [
                    confronto.jogador_a1_id, confronto.jogador_a2_id,
                    confronto.jogador_b1_id, confronto.jogador_b2_id
                ]
                for jogador_id in jogadores_ids:
                    pontuacoes_jogadores[jogador_id] = max(
                        pontuacoes_jogadores.get(jogador_id, 0),
                        RankingManager.PONTOS['quartas']
                    )
            
            # Processar semi-finais (50 pontos)
            for confronto in por_fase['semi']:
                jogadores_ids = [
                    confronto.jogador_a1_id, confronto.jogador_a2_id,
                    confronto.jogador_b1_id, confronto.jogador_b2_id
                ]
                for jogador_id in jogadores_ids:
                    pontuacoes_jogadores[jogador_id] = max(
                        pontuacoes_jogadores.get(jogador_id, 0),
                        RankingManager.PONTOS['semi']
                    )
            
            # Processar final
            final = por_fase['final']
            if final:
                if final.pontos_dupla_a > final.pontos_dupla_b:
                    # Time A ganhou
                    campeoes = [final.jogador_a1_id, final.jogador_a2_id]
                    vices = [final.jogador_b1_id, final.jogador_b2_id]
                else:
                    # Time B ganhou
                    campeoes = [final.jogador_b1_id, final.jogador_b2_id]
                    vices = [final.jogador_a1_id, final.jogador_a2_id]
                
                # Pontuação para campeões (125 pontos)
                for jogador_id in campeoes:
                    pontuacoes_jogadores[jogador_id] = max(
                        pontuacoes_jogadores.get(jogador_id, 0),
                        RankingManager.PONTOS['campeao']
                    )
                
                # Pontuação para vices (75 pontos)
                for jogador_id in vices:
                    pontuacoes_jogadores[jogador_id] = max(
                        pontuacoes_jogadores.get(jogador_id, 0),
                        RankingManager.PONTOS['vice']
                    )
            
            # Atualizar pontuações no banco de dados
            for jogador_id, pontuacao in pontuacoes_jogadores.items():
                jogador = Jogador.query.get(jogador_id)
                if jogador:
                    jogador.pontuacao = pontuacao
            
            db.session.commit()
            logger.info(f"Pontuação calculada com sucesso para o torneio {torneio_id}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao calcular pontuação do torneio {torneio_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def obter_ranking():
        """Obtém o ranking completo dos jogadores por pontuação"""
        try:
            # Consulta SQL para agrupar jogadores pelo nome, somar pontuações e contar torneios
            sql = text("""
                SELECT 
                    jp.nome, 
                    SUM(COALESCE(j.pontuacao, 0)) as pontos_totais,
                    COUNT(DISTINCT j.torneio_id) as torneios_jogados
                FROM 
                    jogador_permanente jp
                LEFT JOIN
                    jogador j ON jp.id = j.jogador_permanente_id
                GROUP BY 
                    jp.nome 
                ORDER BY 
                    pontos_totais DESC, 
                    jp.nome ASC
            """)
            
            resultado = db.session.execute(sql).fetchall()
            
            # Formatar o resultado com posições corretas
            ranking = []
            posicao_atual = 1
            pontuacao_anterior = None
            
            for i, (nome, pontos, torneios) in enumerate(resultado):
                # Se a pontuação for diferente da anterior, atualizar a posição
                if pontos != pontuacao_anterior and i > 0:
                    posicao_atual = i + 1
                
                ranking.append({
                    'posicao': posicao_atual,
                    'nome': nome,
                    'pontos': pontos or 0,
                    'torneios': torneios or 0  # Adicionando o número de torneios
                })
                
                pontuacao_anterior = pontos
            
            return ranking
    
        except Exception as e:
            logger.error(f"Erro ao obter ranking: {str(e)}")
            return []