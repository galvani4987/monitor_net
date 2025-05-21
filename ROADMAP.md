# Roadmap de Melhorias para o Real-time Network Latency Monitor

Este documento descreve o plano de implementação para as melhorias sugeridas no projeto `monitor_net`. Cada seção representa uma área de melhoria com seus respectivos passos.

## Fase 1: Fundações e Estilo

### 1.1. Consistência de Estilo de Código
* **Objetivo:** Garantir um código limpo, legível e padronizado.
* **Ferramentas:** `flake8` para linting, `black` para formatação.
* **Passos:**
    * [ ] Instalar `flake8` e `black` no ambiente de desenvolvimento (`pip install flake8 black`).
    * [ ] Executar `flake8 monitor_net.py` e corrigir todos os avisos e erros reportados.
    * [ ] Executar `black monitor_net.py` para formatar o código automaticamente.
    * [ ] Adicionar um arquivo de configuração para `flake8` (ex: `.flake8`) se personalizações forem necessárias.
    * [ ] Considerar adicionar um hook de pre-commit (ex: com `pre-commit`) para automatizar a verificação de estilo antes de cada commit.

### 1.2. Constantes para ANSI Codes e "Magic Numbers"
* **Objetivo:** Melhorar a legibilidade e manutenibilidade substituindo valores hardcoded por constantes nomeadas.
* **Arquivo Principal:** `monitor_net.py`
* **Passos:**
    * [ ] Identificar todos os códigos de escape ANSI (ex: `\033[H`, `\033[J`, `\033[?25l`, `\033[?25h`) em `monitor_net.py`.
    * [ ] Definir constantes nomeadas para cada código ANSI no início do script (ex: `ANSI_CURSOR_HOME = "\033[H"`).
    * [ ] Identificar "números mágicos" (ex: `15` para `overhead_lines`, `MAX_DATA_POINTS = 200`, `CONSECUTIVE_FAILURES_ALERT_THRESHOLD = 3`, `STATUS_MESSAGE_RESERVED_LINES = 3`). Alguns já são constantes, verificar se todos os relevantes estão cobertos.
    * [ ] Substituir todas as ocorrências dos valores hardcoded pelas constantes definidas.

## Fase 2: Refatoração Principal

### 2.1. Encapsulamento com Classes
* **Objetivo:** Melhorar a organização do código, reduzir o uso de variáveis globais e facilitar testes e extensões futuras.
* **Arquivo Principal:** `monitor_net.py`
* **Passos:**
    * [ ] Definir uma nova classe, por exemplo, `NetworkMonitor`, em `monitor_net.py`.
    * [ ] Mover as variáveis globais de estado (ex: `latency_plot_values`, `latency_history_real_values`, `consecutive_ping_failures`, `connection_status_message`, `total_monitoring_time_seconds`) para se tornarem atributos de instância da classe (inicializados no `__init__`).
    * [ ] Mover as variáveis de configuração padrão (ex: `DEFAULT_HOST`, `DEFAULT_PING_INTERVAL_SECONDS`) para se tornarem atributos de classe ou de instância, conforme apropriado. Argumentos de CLI podem atualizar os atributos da instância.
    * [ ] Converter as funções principais (`measure_latency`, `update_display_and_status`, e a lógica do loop `while True` dentro de `main`) em métodos da classe `NetworkMonitor`.
    * [ ] O método `__init__` da classe pode receber os argumentos parseados da CLI para configurar a instância.
    * [ ] A função `main` original será simplificada para:
        * Parsear os argumentos da CLI.
        * Instanciar `NetworkMonitor` com esses argumentos.
        * Chamar um método principal da instância (ex: `monitor.run()`) que contém o loop de monitoramento.
    * [ ] Garantir que o tratamento de `KeyboardInterrupt` e a restauração do cursor/terminal (`termios`) sejam gerenciados corretamente dentro da classe ou pelo método `run`.

### 2.2. Refatoração de Funções Longas
* **Objetivo:** Aumentar a clareza e modularidade da função `update_display_and_status` (que se tornará um método de classe).
* **Método Alvo:** `NetworkMonitor.update_display_and_status` (após refatoração 2.1).
* **Passos:**
    * [ ] Analisar o método `update_display_and_status` e identificar blocos lógicos distintos.
    * [ ] Para cada bloco, criar um novo método privado (prefixado com underscore) dentro da classe `NetworkMonitor`. Sugestões:
        * `_display_status_message(self)`
        * `_prepare_plot_area(self)` (para obter tamanho do terminal, calcular `plot_height`, `plot_width`)
        * `_configure_plot_axes_and_labels(self)`
        * `_plot_latency_series(self)` (para `pltx.plot` e `pltx.scatter`)
        * `_render_plot(self)` (para `pltx.show()`)
        * `_display_statistics(self)`
    * [ ] O método `update_display_and_status` original chamará esses novos métodos privados em sequência.

## Fase 3: Funcionalidades e Robustez

### 3.1. Aprimoramento do Tratamento de Erros e Logging
* **Objetivo:** Implementar um sistema de logging mais flexível e estruturado.
* **Arquivo Principal:** `monitor_net.py`
* **Passos:**
    * [ ] Importar o módulo `logging` do Python.
    * [ ] Configurar um logger básico no início do script ou no `__init__` da classe `NetworkMonitor` (ex: `logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')`).
    * [ ] Substituir chamadas de `print()` e `sys.stdout.write()` usadas para mensagens de status, avisos e erros por chamadas ao logger (ex: `logger.info()`, `logger.warning()`, `logger.error()`, `logger.critical()`, `logger.debug()`).
    * [ ] Revisar o tratamento da exceção `FileNotFoundError` para o comando `ping` para garantir que a mensagem seja clara e registrada adequadamente através do logger, evitando duplicação.

### 3.2. Clareza na Lógica de Plotagem de Falhas (Revisão)
* **Objetivo:** Assegurar que a lógica para representar falhas no gráfico seja clara e bem documentada.
* **Arquivo Principal:** `monitor_net.py`
* **Passos:**
    * [ ] Revisar e adicionar comentários detalhados explicando por que `latency_plot_values` usa `0` para falhas e `latency_history_real_values` usa `None`, e como ambos são usados na plotagem.
    * [ ] (Opcional) Considerar se uma estrutura de dados unificada para cada ponto de histórico (ex: um `collections.namedtuple` ou uma pequena classe `DataPoint` com atributos como `real_value` e `plot_value`) simplificaria a lógica ou melhoraria a legibilidade. Se não houver um benefício claro, manter a estrutura atual com bons comentários.

### 3.3. Revisão de Docstrings e Comentários
* **Objetivo:** Garantir que todo o código seja bem documentado.
* **Arquivo Principal:** `monitor_net.py`
* **Passos:**
    * [ ] Percorrer todas as classes e métodos/funções.
    * [ ] Escrever ou atualizar docstrings para cada um, explicando seu propósito, argumentos (tipos e descrição), o que retorna, e quaisquer exceções que pode levantar. Usar um formato padrão (ex: reStructuredText ou Google style).
    * [ ] Adicionar/revisar comentários inline para seções de código complexas ou lógicas não óbvias.

## Fase 4: Testes e Manutenção

### 4.1. Implementação de Testes Automatizados
* **Objetivo:** Criar um conjunto de testes para garantir a corretude do código e facilitar refatorações futuras.
* **Ferramentas:** `unittest` (padrão) ou `pytest`.
* **Passos:**
    * [ ] Escolher um framework de testes (`pytest` é geralmente recomendado por sua simplicidade).
    * [ ] Criar um diretório de testes (ex: `tests/`).
    * [ ] Configurar o ambiente para rodar os testes.
    * [ ] Escrever testes unitários para:
        * O método de parsing da saída do `ping` (dentro de `measure_latency`), cobrindo diferentes formatos de saída válidos, casos de falha, e timeouts. (Isso pode exigir mockar `subprocess.run`).
        * Funções/métodos que realizam cálculos de estatísticas.
        * Validação de argumentos da CLI.
        * (Se classe for implementada) Testar a inicialização da classe e a lógica de seus métodos principais.
    * [ ] Considerar testes de integração simples que simulam a execução do monitor por alguns ciclos (pode ser mais complexo).
    * [ ] Integrar a execução dos testes em um script ou Makefile.

### 4.2. Melhorias no Script `run_monitor.sh` (Menor)
* **Objetivo:** Pequenos ajustes para robustez.
* **Arquivo Principal:** `run_monitor.sh`
* **Passos:**
    * [ ] (Opcional) Adicionar uma verificação se o arquivo `REQUIREMENTS_FILE` (`requirements.txt`) está vazio antes de chamar `pip install -r`. Se estiver vazio, talvez pular o passo de instalação ou emitir uma mensagem. O `pip` geralmente lida bem com isso, então é de baixa prioridade.

## Considerações Adicionais
* **Controle de Versão:** Usar Git e fazer commits pequenos e descritivos para cada passo ou grupo lógico de mudanças.
* **Branches:** Considerar o uso de feature branches para melhorias maiores (ex: refatoração para classe, implementação de testes).
* **Revisão de Código:** Se possível, ter outra pessoa revisando as mudanças.

Este roadmap é uma sugestão e pode ser ajustado conforme necessário. Recomenda-se focar primeiro nas melhorias que trarão maior impacto na organização e manutenibilidade do código.
