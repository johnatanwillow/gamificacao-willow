FROM python:3.13.5-alpine3.22
# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia o arquivo de dependências para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências
# --no-cache-dir: Desabilita o cache do pip, o que reduz o tamanho da imagem
# --upgrade pip: Garante que estamos usando a versão mais recente do pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho
COPY . .
# Expõe a porta em que o app será executado
EXPOSE 8000

# Comando para executar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]