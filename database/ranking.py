from sqlalchemy import text
from database.db import db
from database.models import Jogador, Torneio, ConfrontoEliminatoria
import logging

logger = logging.getLogger(__name__)

class RankingManager:
    """Classe para gerenciar o sistema de pontuação e ranking dos jogadores"""
    
    # Pontuação para cada fase
    PONTOS = {
        'quartas': 30,
        'semi': 50,
        'vice': 75,
        'campeao': 125
    }
    
    @staticmethod
    def atualizar_pontuacao_jogador(jogador_id, pontos_a_adicionar):
        """Adiciona pontos ao jogador"""
        try:
            jogador = Jogador.query.get(jogador_id)
            if jogador:
                # Para garantir que a pontuação nunca fique negativa
                jogador.pontuacao = max(0, (jogador.pontuacao or 0) + pontos_a_adicionar)
                db.session.commit()
                logger.info(f"Pontuação do jogador {jogador.nome} atualizada: +{pontos_a_adicionar} pontos")
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
            
            # Buscar confrontos da fase eliminatória
            confrontos = ConfrontoEliminatoria.query.filter_by(torneio_id=torneio_id).all()
            
            # Organizar por fase
            por_fase = {'quartas': [], 'semi': [], 'final': None}
            for confronto in confrontos:
                if confronto.fase == 'final':
                    por_fase['final'] = confronto
                else:
                    por_fase[confronto.fase].append(confronto)
            
            # Processar quartas de final
            for confronto in por_fase['quartas']:
                # Jogadores da fase de quartas (tanto vencedores quanto perdedores)
                jogadores_ids = [
                    confronto.jogador_a1_id, confronto.jogador_a2_id,
                    confronto.jogador_b1_id, confronto.jogador_b2_id
                ]
                for jogador_id in jogadores_ids:
                    RankingManager.atualizar_pontuacao_jogador(jogador_id, RankingManager.PONTOS['quartas'])
            
            # Processar semi-finais
            for confronto in por_fase['semi']:
                # Jogadores da fase de semi (todos ganham a pontuação)
                jogadores_ids = [
                    confronto.jogador_a1_id, confronto.jogador_a2_id,
                    confronto.jogador_b1_id, confronto.jogador_b2_id
                ]
                for jogador_id in jogadores_ids:
                    RankingManager.atualizar_pontuacao_jogador(jogador_id, RankingManager.PONTOS['semi'])
            
            # Processar final
            final = por_fase['final']
            if final:
                # Determinar vencedor e perdedor
                if final.pontos_dupla_a > final.pontos_dupla_b:
                    # Time A ganhou
                    campeoes = [final.jogador_a1_id, final.jogador_a2_id]
                    vices = [final.jogador_b1_id, final.jogador_b2_id]
                else:
                    # Time B ganhou
                    campeoes = [final.jogador_b1_id, final.jogador_b2_id]
                    vices = [final.jogador_a1_id, final.jogador_a2_id]
                
                # Atribuir pontos aos campeões
                for jogador_id in campeoes:
                    RankingManager.atualizar_pontuacao_jogador(jogador_id, RankingManager.PONTOS['campeao'])
                
                # Atribuir pontos aos vices
                for jogador_id in vices:
                    RankingManager.atualizar_pontuacao_jogador(jogador_id, RankingManager.PONTOS['vice'])
            
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
            # Consulta SQL para agrupar jogadores pelo nome e somar pontuações
            sql = text("""
                SELECT 
                    nome, 
                    SUM(pontuacao) as pontos_totais 
                FROM 
                    jogador 
                GROUP BY 
                    nome 
                ORDER BY 
                    pontos_totais DESC, 
                    nome ASC
            """)
            
            resultado = db.session.execute(sql).fetchall()
            
            # Formatar o resultado com posições corretas
            ranking = []
            posicao_atual = 1
            pontuacao_anterior = None
            
            for i, (nome, pontos) in enumerate(resultado):
                # Se a pontuação for diferente da anterior, atualizar a posição
                if pontos != pontuacao_anterior and i > 0:
                    posicao_atual = i + 1
                
                ranking.append({
                    'posicao': posicao_atual,
                    'nome': nome,
                    'pontos': pontos or 0
                })
                
                pontuacao_anterior = pontos
            
            return ranking
        
        except Exception as e:
            logger.error(f"Erro ao obter ranking: {str(e)}")
            return []