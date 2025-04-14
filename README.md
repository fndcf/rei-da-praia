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

## 🚀 Instalação e Configuração

### Pré-requisitos
- Python 3.10 ou superior
- PostgreSQL
- pip (gerenciador de pacotes do Python)

### Passos para Instalação

1. **Clone o repositório**
   ```bash
   git clone https://github.com/fndcf/rei-da-praia.git
   cd rei-da-praia
   ```

2. **Crie e ative um ambiente virtual**
   ```bash
   python -m venv venv
   
   # No Windows
   venv\Scripts\activate
   
   # No Linux/macOS
   source venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente**  
   Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   ```
   SECRET_KEY=sua_chave_secreta_aqui
   DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_do_banco
   ```

5. **Inicialize o banco de dados**
   ```bash
   # Certifique-se de que o PostgreSQL está rodando
   # Crie o banco de dados
   createdb nome_do_banco
   
   # A aplicação criará as tabelas automaticamente ao iniciar
   ```

6. **Execute a aplicação**
   ```bash
   python app.py
   ```
   Acesse http://localhost:5000 no seu navegador.

## 📷 Exemplos de Uso

### Criação de um Novo Torneio

1. Na página inicial, clique em "Novo Torneio"
2. Selecione o formato do torneio (20, 24, 28 ou 32 jogadores)
3. Digite os nomes dos jogadores separados por vírgula ou use o botão "Selecionar Jogadores Existentes"
4. Digite um nome para o torneio e clique em "Sortear Grupos"
5. O sistema organizará os jogadores em grupos de 4

### Gerenciamento da Fase de Grupos

1. Para cada confronto, registre os resultados digitando os pontos de cada dupla
2. Salve os resultados de cada grupo ou use "Salvar Jogos" para salvar todos os grupos de uma vez
3. Após registrar todos os resultados, clique em "Abrir Fase Eliminatória"

### Fase Eliminatória

1. Registre os resultados das quartas de final
2. Clique em "Gerar Semi-finais" e registre os resultados
3. Clique em "Gerar Final" e registre o resultado final
4. Finalize o torneio para atualizar o ranking e visualizar os campeões

## 🤝 Como Contribuir

Agradecemos seu interesse em contribuir com o projeto! Aqui estão algumas diretrizes:

1. **Fork o repositório**
2. **Crie uma branch para sua feature**
   ```bash
   git checkout -b feature/nova-funcionalidade
   ```
3. **Commit suas mudanças**
   ```bash
   git commit -m 'Adiciona nova funcionalidade'
   ```
4. **Push para a branch**
   ```bash
   git push origin feature/nova-funcionalidade
   ```
5. **Abra um Pull Request**

### Padrões de Código
- Siga a PEP 8 para código Python
- Use docstrings para documentar funções e classes
- Mantenha o código limpo e bem comentado
- Escreva testes para novas funcionalidades

## 📂 Estrutura do Projeto

```
sistema-torneios-beach-tennis/
├── app.py                 # Ponto de entrada da aplicação
├── config.py              # Configurações da aplicação
├── requirements.txt       # Dependências do projeto
├── runtime.txt            # Versão do Python para deploy
├── .env                   # Variáveis de ambiente (não versionado)
├── database/              # Módulos relacionados ao banco de dados
│   ├── db.py              # Configuração do SQLAlchemy
│   ├── models.py          # Modelos de dados
│   └── ranking.py         # Lógica do sistema de ranking
├── routes/                # Rotas da aplicação
│   ├── main.py            # Rotas principais
│   ├── groups.py          # Rotas da fase de grupos
│   └── playoffs.py        # Rotas da fase eliminatória
├── static/                # Arquivos estáticos
│   ├── style.css          # Folhas de estilo CSS
│   └── logo_campeonato.png # Imagens e outros assets
└── templates/             # Templates HTML
    ├── base.html          # Template base
    ├── home.html          # Página inicial
    ├── sorteio-grupos.html # Página de sorteio
    └── ...                # Outros templates
```

## 📊 Status do Projeto

- **Estado atual**: Em desenvolvimento ativo
- **Última versão estável**: 1.0.0

### Roadmap

- [ ] Implementação de gráficos de desempenho para jogadores
- [ ] Sistema de autenticação de usuários
- [ ] API para acesso externo aos dados
- [ ] Integração com aplicativos móveis
- [ ] Suporte para torneios com diferentes formatos de pontuação

## ❓ Resolução de Problemas

### Problemas Comuns

1. **Erro de conexão com o banco de dados**
   - Verifique se o PostgreSQL está em execução
   - Confira as credenciais no arquivo .env
   - Certifique-se de que o banco de dados existe

2. **Erro ao sortear grupos**
   - Verifique se o número de jogadores corresponde ao formato selecionado
   - Certifique-se de que não há nomes duplicados na lista

3. **Problemas com a fase eliminatória**
   - Todos os resultados da fase de grupos devem estar preenchidos
   - Não pode haver empates nos confrontos

### Contato para Suporte

Se encontrar algum problema não listado acima ou tiver sugestões, abra uma issue no repositório do projeto.

## 🙏 Agradecimentos

- Agradecemos a todos os jogadores e organizadores de torneios que forneceram feedback valioso para o desenvolvimento deste sistema
- Inspirado nos torneios de Beach Tennis realizados em clubes e praias do Brasil
