# Sistema de Gerenciamento de Torneios de Beach Tennis

Uma aplicação web completa desenvolvida com Python e Flask para gerenciar torneios de Beach Tennis, com suporte a diferentes formatos, acompanhamento de partidas, ranking de jogadores e histórico completo.

## 📋 Funcionalidades

### 🏆 Gerenciamento de Torneios

- **Múltiplos Formatos**: Suporte para torneios de 20, 24, 28 ou 32 jogadores
- **Sorteio Automático**: Distribuição aleatória dos jogadores em grupos de 4
- **Fase de Grupos**: Gerenciamento completo dos confrontos em grupo
- **Fase Eliminatória**: Sistema de mata-mata com quartas, semifinais e final
- **Ranking de Jogadores**: Sistema de pontuação que gera um ranking global

### 🎮 Interface Intuitiva

- **Design Responsivo**: Funciona em dispositivos móveis e desktop
- **Validações Inteligentes**: Evita erros de digitação e dados inconsistentes
- **Feedback Visual**: Destaques para vencedores, alertas e confirmações
- **Histórico Detalhado**: Acompanhamento de todas as fases do torneio

## 📱 Principais Telas

### Página Inicial (Home)
- **Torneios Ativos**: Mostra se há um torneio em andamento
- **Histórico**: Lista de torneios anteriores com campeões e vice-campeões
- **Ranking**: Top 10 jogadores com mais pontos no sistema
- **Busca de Jogadores**: Pesquisa por nome com autocompletar

### Sorteio e Fase de Grupos
- **Configuração de Torneio**: Escolha do formato e nome do torneio
- **Seleção de Jogadores**: Entrada manual ou seleção de jogadores cadastrados
- **Grupos Gerados**: Visualização dos grupos sorteados
- **Registro de Resultados**: Interface para inserção dos resultados dos jogos
- **Validações**: Impede empates e controla a faixa de pontuação (0-7)

### Fase Eliminatória
- **Quartas de Final**: Jogos gerados com base na classificação dos grupos
- **Semifinais**: Confrontos dos vencedores das quartas
- **Final**: Confronto final para definir campeões
- **Histórico de Jogos**: Acompanhamento visual de todos os confrontos
- **Reset de Resultados**: Possibilidade de reiniciar a fase eliminatória

### Histórico e Estatísticas
- **Detalhes do Torneio**: Visualização completa de um torneio específico
- **Perfil de Jogador**: Histórico e estatísticas individuais de cada jogador
- **Ranking Completo**: Classificação geral de todos os jogadores

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python + Flask
- **Banco de Dados**: SQLAlchemy + PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Persistência**: Sistema de sessão e banco de dados relacional

## 🗃️ Estrutura do Banco de Dados

- **JogadorPermanente**: Cadastro central de jogadores
- **ParticipacaoTorneio**: Registro da participação de jogadores em torneios
- **Jogador**: Informações específicas do jogador em um torneio
- **Torneio**: Dados gerais do torneio
- **Confronto**: Jogos da fase de grupos
- **ConfrontoEliminatoria**: Jogos da fase eliminatória

## 🚀 Fluxo de Uso

1. **Criar Torneio**: Definir formato, nomear e selecionar jogadores
2. **Fase de Grupos**: Registrar resultados dos confrontos em grupos
3. **Fase Eliminatória**: Gerenciar quartas, semifinais e final
4. **Finalizar Torneio**: Registrar vencedores e atualizar ranking
5. **Consultar Histórico**: Acessar detalhes de torneios e perfis de jogadores

## ⭐ Funcionalidades Destacadas

### Na Aba de Sorteio
- **Validação de Jogadores**: Verifica a quantidade correta de jogadores para o formato escolhido
- **Seleção Facilitada**: Botão para escolher jogadores já cadastrados
- **Validações Inteligentes**: Botão de sorteio só ativa quando todos os campos estão corretamente preenchidos
- **Prevenção de Duplicatas**: Verifica se já existe torneio com o mesmo nome

### Na Fase de Grupos
- **Validação de Resultados**: Impede empates nos confrontos
- **Salvar por Grupo**: Botões individuais para salvar cada grupo
- **Salvar Todos**: Opção para salvar todos os resultados de uma vez
- **Controle de Avanço**: Validação para garantir que todos os resultados foram preenchidos antes de avançar

### Na Fase Eliminatória
- **Visualização Hierárquica**: Exibição clara das fases do torneio
- **Histórico Atualizado**: Acompanhamento visual dos jogos já realizados
- **Controle de Progresso**: Botões de avanço só aparecem quando a fase anterior está completa
- **Reset Seletivo**: Possibilidade de resetar apenas a fase eliminatória

### No Histórico e Estatísticas
- **Perfil Detalhado**: Estatísticas completas de cada jogador
- **Ranking Global**: Sistema de pontuação que valoriza as melhores colocações
- **Visualização de Torneios**: Acesso a todos os detalhes de torneios finalizados
