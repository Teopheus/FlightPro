# Usa uma imagem leve do Python
FROM python:3.9-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para o Pillow (manipulação de imagem)
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para dentro do container
COPY . .

# CORREÇÃO AQUI: trocado "-path" por "-p"
RUN mkdir -p static/generated && chmod 777 static/generated

# Expõe a porta 5000
EXPOSE 5000

# Comando para rodar o app
CMD ["python", "app.py"]