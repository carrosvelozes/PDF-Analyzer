# PDF Analyzer

![PDF Analyzer Interface](https://i.imgur.com/An026pf.png)

PDF Analyzer é uma aplicação web que utiliza inteligência artificial para analisar documentos PDF e responder perguntas sobre seu conteúdo, de forma rápida e intuitiva.

## Requisitos do Sistema
- Python 3.7 ou superior
- 8GB de RAM (mínimo recomendado)
- 10GB de espaço em disco (para modelos e dependências)
- Conexão com internet para download inicial de dependências
- Windows 10/11, Linux ou macOS

## Funcionalidades
- **Upload de PDF:** Faça upload de qualquer arquivo PDF para análise.
- **Análise Inteligente:** O backend processa o PDF, extrai o texto e gera estatísticas do documento.
- **Chat com IA:** Permite ao usuário fazer perguntas sobre o conteúdo do PDF, recebendo respostas precisas baseadas em IA (ex: modelo DeepSeek R1).
- **Interface Moderna:** Frontend responsivo, com dark mode, navegação intuitiva e chat interativo.
- **Suporte a múltiplos idiomas:** Detecta e responde perguntas em diferentes idiomas.

## Tecnologias Utilizadas
### Backend
- **Python 3.7+**
- **FastAPI** — API REST moderna e performática
- **PyTorch, Transformers, Sentence Transformers** — Modelos de IA e NLP
- **FAISS** — Busca vetorial para respostas contextuais
- **PyPDF2, pdfplumber, pdfminer** — Processamento e extração de texto de PDFs
- **Uvicorn** — Servidor ASGI

### Frontend
- **HTML5, CSS3, JavaScript**
- Interface customizada, sem frameworks, com dark mode e navegação por seções

## Instalação
### 1. Ollama (Requisito Principal)
1. Baixe e instale o Ollama do site oficial: [https://ollama.ai/download](https://ollama.ai/download)
2. Após a instalação, baixe o modelo DeepSeek R1:
   ```bash
   ollama pull deepseekr1
   ```
3. Verifique se o modelo foi baixado corretamente:
   ```bash
   ollama list
   ```

### 2. Backend
1. Acesse a pasta `backend`:
   ```bash
   cd backend
   ```
2. Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate    # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Instale o spaCy e baixe o modelo de linguagem:
   ```bash
   python -m spacy download pt_core_news_lg
   ```
5. Baixe os recursos do NLTK:
   ```bash
   python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
   ```
6. Inicie o servidor:
   ```bash
   python app.py
   ```

### 3. Frontend
1. Acesse a pasta `frontend`:
   ```bash
   cd frontend
   ```
2. Inicie o servidor HTTP Python:
   ```bash
   python -m http.server 8000
   ```
3. Abra o navegador e acesse `http://localhost:8000`

## Dependências Principais
### Backend
- FastAPI e Uvicorn para o servidor web
- PyTorch e Transformers para processamento de IA
- FAISS para busca vetorial
- PyPDF2, pdfplumber e pdfminer para processamento de PDFs
- spaCy e NLTK para processamento de linguagem natural
- Ollama para integração com o modelo DeepSeek R1

### Frontend
- HTML5, CSS3 e JavaScript puro
- Font Awesome para ícones
- Google Fonts (Inter e Space Grotesk)
- CDN para recursos externos (não requer instalação)

## Solução de Problemas
1. Se o Ollama não iniciar:
   - Verifique se o serviço está rodando
   - Reinicie o computador
   - Reinstale o Ollama

2. Se o backend não iniciar:
   - Verifique se todas as dependências foram instaladas
   - Confirme se o ambiente virtual está ativado
   - Verifique se o modelo spaCy foi baixado

3. Se o frontend não carregar:
   - Verifique se o servidor HTTP está rodando
   - Limpe o cache do navegador
   - Verifique se a porta 8000 está disponível

## Como Usar
1. Abra o frontend (`frontend/index.html`) no navegador.
2. Faça upload de um arquivo PDF.
3. Aguarde o processamento e visualize as estatísticas do documento.
4. Utilize o chat para fazer perguntas sobre o conteúdo do PDF.

## Estrutura do Projeto
```
Projeto web/
├── backend/
│   ├── app.py
│   ├── model_manager.py
│   ├── pdf_processor.py
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── styles.css
└── README.md
```

## Créditos
- **Desenvolvedor:** Leonardo Souza Faria de Moraes ([GitHub](https://github.com/carrosvelozes))
- **Orientação:** Prof. Carlos Eduardo Beluzo
- **Contato:** moraes.souza@aluno.ifsp.edu.br

## Licença
Este projeto é acadêmico e pode ser adaptado para fins educacionais e de pesquisa. 
