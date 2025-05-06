# PDF Analyzer

PDF Analyzer é uma aplicação web que utiliza inteligência artificial para analisar documentos PDF e responder perguntas sobre seu conteúdo, de forma rápida e intuitiva.

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
### Backend
1. Acesse a pasta `backend`:
   ```bash
   cd backend
   ```
2. (Recomendado) Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate    # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o servidor:
   ```bash
   uvicorn app:app --reload
   ```

### Frontend
1. Acesse a pasta `frontend` e abra o arquivo `index.html` no navegador.
   - Não há dependências extras para rodar o frontend.

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
