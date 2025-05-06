#!/bin/bash

# Nome do diretório do ambiente virtual
VENV_DIR=".venv_monitor_net"
# Nome do script Python a ser executado
PYTHON_SCRIPT="monitor_net.py"
# Nome do arquivo de requisitos
REQUIREMENTS_FILE="requirements.txt"

# Garante que o script opera relativo ao seu próprio local
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Caminhos completos para os executáveis e arquivos dentro do diretório do script
VENV_PATH="$SCRIPT_DIR/$VENV_DIR"
PYTHON_EXEC="$VENV_PATH/bin/python"
PIP_EXEC="$VENV_PATH/bin/pip"
SCRIPT_TO_RUN_PATH="$SCRIPT_DIR/$PYTHON_SCRIPT"
REQUIREMENTS_FILE_PATH="$SCRIPT_DIR/$REQUIREMENTS_FILE"

echo "--- Monitor de Conexão ---"

# 1. Verifica se o Python 3 está disponível
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python 3 não encontrado. Por favor, instale o Python 3."
    exit 1
fi

# 2. Cria o ambiente virtual se não existir
if [ ! -d "$VENV_PATH" ]; then
    echo "INFO: Criando ambiente virtual em '$VENV_PATH'..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao criar o ambiente virtual. Verifique se o pacote 'python3-venv' (ou similar) está instalado."
        exit 1
    fi
    echo "INFO: Ambiente virtual criado com sucesso."
else
    echo "INFO: Ambiente virtual '$VENV_DIR' já existe."
fi

# 3. Instala/atualiza as dependências usando o pip do ambiente virtual
#    Verifica se o requirements.txt existe
if [ ! -f "$REQUIREMENTS_FILE_PATH" ]; then
    echo "ERRO: Arquivo '$REQUIREMENTS_FILE' não encontrado em '$SCRIPT_DIR'."
    exit 1
fi

echo "INFO: Instalando/atualizando dependências de '$REQUIREMENTS_FILE' no ambiente virtual..."
"$PIP_EXEC" install --disable-pip-version-check --no-cache-dir -r "$REQUIREMENTS_FILE_PATH"
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar dependências. Verifique '$REQUIREMENTS_FILE' e sua conexão com a internet."
    exit 1
fi
echo "INFO: Dependências instaladas/atualizadas com sucesso."

# 4. Executa o script Python usando o interpretador Python do ambiente virtual
#    Verifica se o script python existe
if [ ! -f "$SCRIPT_TO_RUN_PATH" ]; then
    echo "ERRO: Script Python '$PYTHON_SCRIPT' não encontrado em '$SCRIPT_DIR'."
    exit 1
fi

echo "INFO: Executando o script '$PYTHON_SCRIPT'..."
echo "--------------------------------------------------"
# Executa o script python. O stdout/stderr do script python irá para o terminal.
"$PYTHON_EXEC" "$SCRIPT_TO_RUN_PATH"

# $? contém o código de saída do último comando executado (o script python)
exit_status=$?
echo "--------------------------------------------------"
echo "INFO: Script '$PYTHON_SCRIPT' finalizado com código de saída: $exit_status."

exit $exit_status
