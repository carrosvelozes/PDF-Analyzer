"""
app.py - Servidor FastAPI principal

Este arquivo implementa o servidor FastAPI que gerencia toda a aplicação:
1. Configuração do servidor e rotas da API REST
2. Upload e processamento de arquivos PDF
3. Endpoint de chat/perguntas sobre o conteúdo do PDF
4. Gerenciamento de recursos (pool de threads, limpeza de arquivos temporários)
5. Verificação de saúde do sistema

O servidor permite que usuários enviem PDFs para análise e, em seguida,
façam perguntas sobre o conteúdo desses documentos, usando um modelo de IA
para responder com base no texto extraído do PDF.
"""

from fastapi import FastAPI, UploadFile, HTTPException, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import tempfile
from model_manager import ModelManager
from pdf_processor import PDFProcessor
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import warnings
import time
import uvicorn
import torch
import requests

# Configurar logging e suprimir warnings específicos
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suprimir warnings específicos
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", category=UserWarning, module="sentence_transformers")



app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar componentes globalmente, mas sem carregar modelo ainda
model_manager = ModelManager()
pdf_processor = PDFProcessor()
executor = ThreadPoolExecutor(max_workers=2)

class ChatMessage(BaseModel):
    message: str

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Endpoint para upload, processamento e indexação de PDF."""
    temp_file_path = None
    try:
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos e o nome do arquivo é obrigatório.")

        # Salvar o arquivo temporariamente de forma segura
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            if not content:
                 raise HTTPException(status_code=400, detail="Arquivo PDF vazio.")
            temp_file.write(content)
            temp_file_path = temp_file.name
            print(f"Arquivo PDF salvo temporariamente em: {temp_file_path}")

        # Processar o PDF com timeout
        print("Iniciando processamento do PDF no executor...")
        try:
            success, message, pages = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    executor,
                    pdf_processor.process_pdf,
                    temp_file_path
                ),
                timeout=120.0  # Aumentado para 120s para PDFs maiores
            )
            print(f"Processamento do PDF concluído. Sucesso: {success}")
        except asyncio.TimeoutError:
            print("Timeout ao processar PDF")
            raise HTTPException(status_code=504, detail="Timeout: O processamento do PDF demorou muito.")
        except Exception as e:
             print(f"Erro durante execução do process_pdf no executor: {e}")
             raise HTTPException(status_code=500, detail=f"Erro interno ao processar PDF: {e}")

        if not success or not pdf_processor.is_loaded():
            print("Falha no processamento do PDF ou PDF não carregado após processamento.")
            raise HTTPException(status_code=500, detail="Erro: Falha ao processar o conteúdo do PDF.")

        # Indexar o PDF com timeout
        print("Iniciando indexação do PDF no executor...")
        try:
            pages_to_index = pdf_processor.get_pages_for_indexing()
            if not pages_to_index:
                 print("Nenhum conteúdo de página para indexar.")
                 raise HTTPException(status_code=500, detail="Erro: Nenhum conteúdo extraído do PDF para consulta.")

            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    executor,
                    model_manager.index_pdf,
                    pages_to_index
                ),
                timeout=60.0  # 60 segundos para indexação
            )
            print("Indexação do PDF concluída com sucesso.")
        except asyncio.TimeoutError:
            print("Timeout ao indexar PDF")
            raise HTTPException(status_code=504, detail="Timeout: A indexação do conteúdo do PDF demorou muito.")
        except Exception as e:
             print(f"Erro durante execução do index_pdf no executor: {e}")
             raise HTTPException(status_code=500, detail=f"Erro interno ao indexar PDF: {e}")

        # Obter estatísticas após processamento e indexação bem-sucedidos
        stats = pdf_processor.get_statistics()
        if not stats["success"]:
            print("Erro ao obter estatísticas após processamento bem-sucedido.")
            raise HTTPException(status_code=500, detail=stats.get("message", "Erro interno ao obter estatísticas do PDF."))

        # Formatar mensagem de resposta para o chat
        response_message = f"""PDF processado e indexado com sucesso!

**Estatísticas do Documento:**
- Páginas Totais: {stats['total_pages']}
- Páginas Processadas: {stats['processed_pages']}
- Palavras Totais: {stats['total_words']}
- Média Palavras/Página: {stats['average_words_per_page']:.1f}
- Idioma: {stats['language'].upper() if stats['language'] != 'N/A' else 'N/A'}

Agora você pode fazer perguntas sobre este documento.
"""
        # Estrutura final da resposta
        response_data = {
            "success": True,
            "message": response_message,
            "statistics": response_message, # Adicionado para garantir compatibilidade com frontend
            "stats": stats
        }

        # Logar EXATAMENTE o que está sendo retornado
        print(f"Retornando resposta para /upload-pdf: {response_data}")

        # Retornar a estrutura
        return response_data

    except HTTPException as http_exc:
         print(f"HTTP Exception em /upload-pdf: {http_exc.detail}")
         raise http_exc
    except Exception as e:
        print(f"Erro inesperado em /upload-pdf: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro inesperado no servidor durante o upload: {str(e)}")
    finally:
        # Tentar remover o arquivo temporário se ele foi criado
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                time.sleep(0.5) # Pequeno delay síncrono
                os.unlink(temp_file_path)
                print(f"Arquivo temporário removido: {temp_file_path}")
            except PermissionError:
                 print(f"Erro de permissão ao remover {temp_file_path}. Pode ainda estar em uso.")
            except Exception as e:
                print(f"Não foi possível remover o arquivo temporário {temp_file_path}: {str(e)}")

def responder_pergunta_simples(pergunta, stats):
    """
    Responde a perguntas específicas sobre o PDF baseado nas estatísticas
    fornecidas, sem usar o modelo de IA.
    """
    pergunta_lower = pergunta.lower()
    
    # Verifica formato de retorno solicitado
    formato_retorno = verificar_formato_retorno(pergunta)
    
    # Verifica perguntas sobre número de páginas
    termos_paginas = ["quantas páginas", "quantas paginas", "número de páginas", "numero de paginas", 
                      "total de páginas", "total de paginas", "páginas tem", "paginas tem"]
    if any(termo in pergunta_lower for termo in termos_paginas):
        resposta = f"O documento tem {stats['total_pages']} página(s)."
        return formatar_resposta(resposta, formato_retorno)
    
    # Verifica perguntas sobre número de palavras
    termos_palavras = ["quantas palavras", "número de palavras", "numero de palavras", 
                       "total de palavras", "palavras tem", "contagem de palavras"]
    if any(termo in pergunta_lower for termo in termos_palavras):
        resposta = f"O documento tem aproximadamente {stats['total_words']} palavra(s)."
        return formatar_resposta(resposta, formato_retorno)
    
    # Verifica perguntas sobre idioma
    termos_idioma = ["qual idioma", "em que idioma", "idioma do", "língua do", "lingua do", 
                     "linguagem do", "escrito em qual"]
    if any(termo in pergunta_lower for termo in termos_idioma):
        resposta = f"O documento está escrito em {stats['language'].upper()}."
        return formatar_resposta(resposta, formato_retorno)
    
    # Verifica perguntas sobre média de palavras por página
    termos_media_palavras = ["média de palavras", "media de palavras", "palavras por página", 
                            "palavras por pagina", "média por página", "media por pagina"]
    if any(termo in pergunta_lower for termo in termos_media_palavras):
        media = stats['average_words_per_page']
        resposta = f"O documento tem uma média de {media:.1f} palavra(s) por página."
        return formatar_resposta(resposta, formato_retorno)
    
    # Verifica perguntas sobre tamanho do documento (simples)
    termos_tamanho = ["tamanho", "grande", "pequeno", "extenso", "longo", "curto"]
    if any(termo in pergunta_lower for termo in termos_tamanho):
        if stats['total_words'] < 100:
            resposta = f"O documento é muito curto, com apenas {stats['total_words']} palavras em {stats['total_pages']} página(s)."
        elif stats['total_words'] < 500:
            resposta = f"O documento é relativamente pequeno, com {stats['total_words']} palavras em {stats['total_pages']} página(s)."
        else:
            resposta = f"O documento é de tamanho médio, com {stats['total_words']} palavras em {stats['total_pages']} página(s)."
        return formatar_resposta(resposta, formato_retorno)
    
    # Se não for uma pergunta simples reconhecida, retorna None
    return None

def formatar_resposta(resposta, formato):
    """
    Formata a resposta de acordo com o formato solicitado.
    """
    if not formato:
        return resposta
        
    if formato == "tópicos":
        return f"- {resposta}"
        
    elif formato == "markdown":
        return f"**Resposta:** {resposta}"
        
    elif formato == "json":
        import json
        return json.dumps({"resposta": resposta}, ensure_ascii=False)
        
    elif formato == "html":
        return f"<p><strong>Resposta:</strong> {resposta}</p>"
        
    elif formato == "tabela":
        return f"| Informação | Valor |\n|------------|-------|\n| Resposta | {resposta} |"
        
    elif formato == "resumo":
        # Para resumo, simplificamos a resposta removendo detalhes
        import re
        resposta_simplificada = re.sub(r'\s*\([^)]*\)', '', resposta)  # Remove texto entre parênteses
        return resposta_simplificada
        
    elif formato == "detalhado":
        # Para formato detalhado, podemos adicionar informações extras
        return f"Detalhamento da informação solicitada:\n{resposta}\nEsta informação foi extraída diretamente dos metadados e estatísticas do documento."
        
    # Se for um formato não implementado ou não reconhecido, retorna a resposta original
    return resposta

@app.post("/chat")
async def chat(message: ChatMessage):
    """Endpoint para chat com o modelo sobre o PDF carregado."""
    if not pdf_processor.is_loaded():
        return {
            "success": False,
            "response": "Nenhum PDF foi carregado. Por favor, carregue um PDF primeiro."
        }
        
    if not message or not message.message.strip():
         return {
            "success": False,
            "response": "Mensagem vazia não permitida."
         }

    user_message = message.message.strip()
    print(f"Recebida pergunta no chat: '{user_message}'")

    try:
        # Obter estatísticas do PDF para respostas rápidas
        stats = pdf_processor.get_statistics()
        
        # Verificar formato solicitado
        formato_resposta = verificar_formato_retorno(user_message)
        
        # Recuperar o conteúdo completo do PDF para resposta direta
        all_content = ""
        for page in pdf_processor.pages:
            if "content" in page:
                all_content += page["content"] + "\n\n"
        
        if not all_content.strip():
            return {
                "success": False,
                "response": "Não foi possível extrair conteúdo do PDF."
            }
        
        # Verificar se é uma saudação simples
        saudacoes = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "hey", "hi", "hello"]
        pergunta_lower = user_message.lower()
        
        if pergunta_lower in saudacoes or pergunta_lower.startswith(tuple(saudacoes)):
            resposta = f"Olá! Posso responder perguntas sobre o PDF que você carregou. O que gostaria de saber sobre o documento?"
            return {
                "success": True,
                "response": formatar_resposta(resposta, formato_resposta)
            }
        
        # Verificar perguntas não relacionadas ao conteúdo do PDF
        perguntas_nao_relacionadas = ["como vai", "tudo bem", "quem é você", "quem e voce", "qual seu nome"]
        if any(frase in pergunta_lower for frase in perguntas_nao_relacionadas):
            resposta = "Desculpe, só posso responder perguntas relacionadas ao conteúdo do PDF carregado."
            return {
                "success": True,
                "response": formatar_resposta(resposta, formato_resposta)
            }
        
        # Responder perguntas simples sobre estatísticas
        resposta_simples = responder_pergunta_simples(user_message, stats)
        if resposta_simples:
            print("Pergunta respondida com resposta rápida sobre estatísticas")
            return {
                "success": True,
                "response": resposta_simples  # Já está formatada
            }
        
        # Para qualquer outra pergunta, usar o modelo de IA
        print("Usando o modelo de IA para responder à pergunta...")
        
        # Obter contexto relevante do PDF usando a busca semântica
        relevant_context = model_manager.search_pdf(user_message)
        
        # Verificar se conseguimos encontrar contexto relevante
        if not relevant_context or "Não foi possível encontrar" in relevant_context:
            print("Contexto não encontrado, usando o conteúdo completo do PDF")
            # Se não encontrou contexto relevante, usar conteúdo completo (limitado)
            if len(all_content) > 4000:  # Limitar tamanho para não sobrecarregar o modelo
                relevant_context = all_content[:4000] + "..."
            else:
                relevant_context = all_content
        
        # Preparar o prompt para o modelo
        prompt = model_manager.format_prompt(relevant_context, user_message)
        
        # Gerar resposta usando o modelo
        ia_response = model_manager.generate_response(prompt)
        
        # Adicionar ao histórico de conversa
        model_manager.add_to_history(user_message, ia_response)
        
        # Retornar a resposta formatada
        return {
            "success": True,
            "response": formatar_resposta(ia_response, formato_resposta)
        }
        
    except Exception as e:
        print(f"Erro inesperado em /chat: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        return {
            "success": False,
            "response": "Ocorreu um erro inesperado ao processar sua pergunta. Por favor, tente novamente."
        }

@app.get("/health")
async def health_check():
    """Verifica a saúde do servidor e o status do modelo."""
    # Para Ollama, verificamos a conexão em vez do modelo carregado
    try:
        ollama_status = requests.get(f"{model_manager.ollama_api_url}/tags", timeout=5)
        model_loaded = ollama_status.status_code == 200
    except:
        model_loaded = False
        
    pdf_processed = pdf_processor.is_loaded()
    return {
        "status": "ok",
        "model_status": "connected" if model_loaded else "not_connected",
        "pdf_status": "processed" if pdf_processed else "no_pdf",
        "model_name": model_manager.model_name,
        "device": model_manager.device
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Limpa recursos ao desligar o servidor."""
    print("!!!!!!! NOVO CODIGO DE SHUTDOWN SENDO EXECUTADO !!!!!!!")
    print("Iniciando processo de desligamento...")
    # Parar o executor de threads (não esperar indefinidamente)
    print("Sinalizando para o executor de threads desligar (wait=False)...")
    executor.shutdown(wait=False) # Alterado para False
    print("Sinal de desligamento enviado ao executor, não esperando mais.")

    # A limpeza dos recursos do model_manager será feita pelo seu __del__
    print("Permitindo que ModelManager.__del__ cuide da limpeza de seus recursos.")

    # Não limpar cache CUDA aqui, deixar para __del__
    print("Processo de desligamento do app concluído (limpeza final pelo GC). ")

def verificar_formato_retorno(pergunta):
    """
    Verifica se a pergunta é sobre o formato em que a resposta deve ser retornada.
    Retorna None se a pergunta não for sobre formato, ou uma string com o formato solicitado.
    """
    pergunta_lower = pergunta.lower()
    
    # Lista de termos que indicam pedido de formatação específica
    termos_formatacao = {
        "tópicos": ["lista de tópicos", "em tópicos", "em forma de tópicos", "formato de tópicos", 
                   "em bullet points", "em pontos", "em itens", "listado", "como lista", 
                   "enumere", "enumerar", "enumerado", "como tópicos", "liste", "listar"],
        
        "tabela": ["em tabela", "formato de tabela", "como tabela", "em forma de tabela", 
                  "organize em tabela", "apresente em tabela", "mostre em tabela", 
                  "formato tabular", "estrutura de tabela", "tabular"],
        
        "resumo": ["resumidamente", "de forma resumida", "em resumo", "sintetize", "síntese", 
                  "versão resumida", "versao resumida", "resuma", "resumo", "sumarize", 
                  "sumário", "sumario", "de forma concisa", "concisamente"],
        
        "detalhado": ["detalhadamente", "em detalhes", "de forma detalhada", "com detalhes", 
                     "explicação detalhada", "explicacao detalhada", "seja detalhado", 
                     "com informações completas", "com informacoes completas", 
                     "de maneira abrangente", "abrangente", "completo", "aprofundado"],
        
        "markdown": ["em markdown", "formato markdown", "use markdown", "com markdown", 
                    "sintaxe markdown", "utilize markdown"],
        
        "html": ["em html", "formato html", "use html", "com html", "sintaxe html", 
                "utilize html", "código html", "codigo html"],
        
        "json": ["em json", "formato json", "use json", "com json", "sintaxe json", 
                "utilize json", "código json", "codigo json", "notação json", "notacao json"],
        
        "gráfico": ["em gráfico", "em grafico", "formato de gráfico", "formato de grafico", 
                   "como gráfico", "como grafico", "visualização", "visualizacao", 
                   "gráfico de barras", "grafico de barras", "gráfico de pizza", 
                   "grafico de pizza", "de forma visual", "visualmente"]
    }
    
    # Padrões para reconhecer pedidos de formatação
    padroes_formatacao = [
        r"responda (?:em|usando|com|no formato(?: de)?|como) ([\w\s]+)",
        r"apresente (?:em|usando|com|no formato(?: de)?|como) ([\w\s]+)",
        r"mostre (?:em|usando|com|no formato(?: de)?|como) ([\w\s]+)",
        r"exiba (?:em|usando|com|no formato(?: de)?|como) ([\w\s]+)",
        r"formate (?:em|usando|como|no formato(?: de)?) ([\w\s]+)",
        r"quero (?:em|no formato(?: de)?|como) ([\w\s]+)",
        r"formato (?:de|em) ([\w\s]+)",
        r"organizado (?:em|como) ([\w\s]+)"
    ]
    
    # Verifica se a pergunta tem algum termo direto de formatação
    for formato, termos in termos_formatacao.items():
        if any(termo in pergunta_lower for termo in termos):
            return formato
    
    # Verifica se a pergunta segue algum padrão de pedido de formatação
    import re
    for padrao in padroes_formatacao:
        match = re.search(padrao, pergunta_lower)
        if match:
            formato_solicitado = match.group(1).strip()
            
            # Mapeia o texto extraído para um formato reconhecido
            for formato, termos in termos_formatacao.items():
                if any(termo.endswith(formato_solicitado) or 
                       termo.startswith(formato_solicitado) or 
                       formato_solicitado in termo
                       for termo in termos):
                    return formato
    
    # Se não encontrou nenhum formato específico
    return None

if __name__ == "__main__":
    print("Iniciando servidor Uvicorn...")
    # Considerar adicionar reload=True apenas para desenvolvimento
    uvicorn.run(app, host="0.0.0.0", port=8000)