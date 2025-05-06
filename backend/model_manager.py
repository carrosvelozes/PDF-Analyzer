"""
model_manager.py - Gerenciador de Modelos de IA

Este módulo é responsável por:
1. Gerenciar a comunicação com o modelo de IA (DeepSeek R1 via Ollama)
2. Processar o contexto e formatar prompts para o modelo
3. Criar e manter o índice vetorial (FAISS) para busca semântica no conteúdo do PDF
4. Detectar o idioma da pergunta e garantir que o modelo responda no mesmo idioma
5. Manter o histórico de conversas para context

Utiliza a API do Ollama para gerar respostas sobre o conteúdo de PDFs,
além de implementar fallbacks quando o serviço não está disponível.
"""

from typing import List, Dict, Tuple
import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
import time
import langdetect  # Para detectar o idioma da pergunta

class ModelManager:
    def __init__(self):
        # Configurar para usar Ollama localmente
        self.ollama_api_url = "http://localhost:11434/api"
        self.model_name = "deepseek-r1"  # Modelo DeepSeek R1
        self.device = "ollama_api"
        self.max_context_length = 8000
        
        # FAISS Index para busca semântica
        self.text_chunks = []
        self.index = None
        self.conversation_history = []
        self.max_history_length = 5
        
        try:
            print("Carregando modelo de embeddings...")
            self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            print("Modelo de embeddings carregado com sucesso")
        except Exception as e:
            print(f"Erro ao carregar modelo de embeddings: {str(e)}")
            self.embedding_model = None
            
        print("ModelManager inicializado para usar Ollama com DeepSeek R1")
        
        # Verificar se o Ollama está disponível
        self._check_ollama_available()
        
    def _detect_language(self, text):
        """Detecta o idioma do texto fornecido"""
        try:
            return langdetect.detect(text)
        except:
            return "pt"  # Padrão para português em caso de erro
            
    def _get_language_instruction(self, lang_code):
        """Retorna a instrução de idioma baseada no código do idioma"""
        language_instructions = {
            "pt": "Responda em português.",
            "en": "Answer in English.",
            "es": "Responda en español.",
            "fr": "Répondez en français.",
            "de": "Antworten Sie auf Deutsch.",
            "it": "Risponda in italiano.",
            # Adicionar mais idiomas conforme necessário
        }
        
        return language_instructions.get(lang_code, "Responda em português.")
        
    def _check_ollama_available(self):
        """Verifica se o Ollama está disponível"""
        try:
            print("Tentando conectar ao Ollama em " + self.ollama_api_url)
            response = requests.get(f"{self.ollama_api_url}/tags", timeout=3)
            if response.status_code == 200:
                # Verificar se o modelo está disponível
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                print(f"Modelos disponíveis no Ollama: {model_names}")
                
                if any(name == self.model_name or name.startswith(self.model_name) for name in model_names):
                    print(f"Modelo {self.model_name} encontrado!")
                    return True
                else:
                    print(f"Aviso: Modelo {self.model_name} não encontrado no Ollama.")
                    print(f"É necessário executar 'ollama pull {self.model_name}' para baixá-lo.")
                    return False
            else:
                print(f"Erro ao conectar ao Ollama: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"Erro de conexão. O serviço Ollama não está rodando em {self.ollama_api_url}")
            print("Execute 'ollama serve' para iniciar o serviço Ollama.")
            return False
        except Exception as e:
            print(f"Erro ao verificar disponibilidade do Ollama: {str(e)}")
            return False

    def load_model(self):
        """
        Método mantido para compatibilidade.
        """
        return self._check_ollama_available()
    
    def index_pdf(self, pages):
        """Cria um índice vetorial do PDF"""
        try:
            # Verificar se pages é uma lista de dicionários com chave "content"
            if isinstance(pages, list):
                if all(isinstance(page, dict) and "content" in page for page in pages):
                    self.text_chunks = [page["content"] for page in pages]
                else:
                    # Se pages é uma lista de strings
                    self.text_chunks = [p for p in pages if isinstance(p, str)]
            else:
                # Caso pages seja uma string única
                self.text_chunks = [pages] if isinstance(pages, str) else []
                
            if not self.text_chunks:
                print("Aviso: Nenhum conteúdo válido para indexar")
                return False
                
            print(f"Indexando {len(self.text_chunks)} trechos de texto")
            # Criar embeddings para cada trecho
            embeddings = np.array([self.embedding_model.encode(text) for text in self.text_chunks])
            
            # Criar e popular o índice FAISS
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
            self.index.add(embeddings)
            
            print("Índice FAISS criado com sucesso")
            return True
        except Exception as e:
            print(f"Erro ao indexar PDF: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def search_pdf(self, query, top_k=3):
        """Busca os trechos mais relevantes para a pergunta"""
        try:
            if self.index is None or not self.text_chunks:
                print("AVISO: Índice FAISS não está pronto ou não há texto para buscar")
                return "Não foi possível encontrar conteúdo relevante no documento."

            query_emb = self.embedding_model.encode(query).reshape(1, -1)
            distances, indices = self.index.search(query_emb, min(top_k, len(self.text_chunks)))
            
            if len(indices[0]) == 0:
                return "Não foi possível encontrar conteúdo relevante no documento."
                
            results = [self.text_chunks[idx] for idx in indices[0] if idx < len(self.text_chunks)]
            return " ".join(results)
        except Exception as e:
            print(f"Erro ao buscar no PDF: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "Erro na busca do conteúdo do documento."
    
    def format_prompt(self, pdf_content: str, user_question: str) -> str:
        """
        Formata o prompt para o modelo com contexto do PDF e histórico.
        """
        if not pdf_content:
            pdf_content = "Não foi possível recuperar conteúdo relevante do documento."
        
        # Truncar conteúdo se necessário
        if len(pdf_content) > self.max_context_length:
            pdf_content = pdf_content[:self.max_context_length] + "..."
            
        history = self.format_history()
        
        # Detectar o idioma da pergunta
        detected_language = self._detect_language(user_question)
        language_instruction = self._get_language_instruction(detected_language)
        print(f"Idioma detectado: {detected_language}")
        
        # Contexto claro e direcionado para o modelo
        prompt = f"""Você é um assistente que analisa PDFs. Sua única função é ler o conteúdo extraído do PDF abaixo e responder questões de forma direta e concisa, sem informações adicionais.

Conteúdo do PDF:
{pdf_content}

{history}

Pergunta: {user_question}

{language_instruction}
Responda de forma direta e concisa, baseando-se exclusivamente no conteúdo do PDF acima.
"""
        return prompt
    
    def generate_response(self, prompt: str) -> str:
        """
        Gera uma resposta usando a API do Ollama com o modelo DeepSeek.
        """
        try:
            print(f"Gerando resposta com modelo {self.model_name} via Ollama...")
            
            # Configurar payload para a API do Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Temperatura baixa para respostas mais factuais
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            # Fazer a chamada para a API do Ollama
            start_time = time.time()
            response = requests.post(f"{self.ollama_api_url}/generate", json=payload, timeout=120)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                ia_response = response_data.get("response", "")
                print(f"Resposta gerada em {elapsed_time:.2f} segundos")
                
                if ia_response and len(ia_response.strip()) > 5:
                    # Processar a resposta para remover pensamento interno
                    cleaned_response = self._clean_thinking_from_response(ia_response)
                    return cleaned_response.strip()
                else:
                    return "O modelo não conseguiu gerar uma resposta adequada."
            else:
                print(f"Erro na API do Ollama: {response.status_code}")
                print(f"Resposta: {response.text}")
                return f"Erro ao gerar resposta: API do Ollama retornou código {response.status_code}"
            
        except Exception as e:
            print(f"Erro ao gerar resposta via Ollama: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return self._fallback_response(prompt)
            
    def _clean_thinking_from_response(self, response: str) -> str:
        """
        Remove padrões de pensamento interno da resposta do modelo.
        """
        # Lista de padrões que indicam "pensamento interno"
        thinking_patterns = [
            r"Okay,\s*I\s*need\s*to\s*figure\s*out.*?(?=[A-Z])",  # Começa com "Okay, I need to figure out"
            r"Let\s*me\s*think\s*about\s*this.*?(?=[A-Z])",  # Começa com "Let me think about this"
            r"I\s*need\s*to\s*understand.*?(?=[A-Z])",  # Começa com "I need to understand"
            r"Looking\s*at\s*the\s*content.*?(?=[A-Z])",  # Contém "Looking at the content"
            r".*?The\s*user\s*(?:asks|wants).*?(?=[A-Z])",  # Contém "The user asks" ou "The user wants"
            r".*?They\s*want.*?(?=[A-Z])",  # Contém "They want"
            r"I\s*should.*?(?=[A-Z])",  # Contém "I should"
            r".*?I will.*?(?=[A-Z])",  # Contém "I will"
            r"Based\s*on\s*the\s*question.*?(?=[A-Z])", # Contém "Based on the question"
            r"The\s*main\s*idea\s*is\s*that.*?(?=[A-Z])", # Contém "The main idea is that"
        ]
        
        # Aplicar os padrões para limpar o texto
        cleaned_text = response
        import re
        
        # Verificar se há um padrão de reflexão seguido por uma resposta real
        for pattern in thinking_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remover espaços em branco extras e linhas em branco
        cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
        
        # Se a resposta começar com O, A, Este, Esta em português ou The, This em inglês
        # é mais provável que seja a resposta real
        matches = re.search(r'(O|A|Este|Esta|The|This|El|La|Este|Esta|Le|La|Ce|Cette|Der|Die|Das|Il|La)\s+\w+', cleaned_text, re.IGNORECASE)
        if matches:
            start_pos = matches.start()
            if start_pos > 0:
                cleaned_text = cleaned_text[start_pos:]
                
        return cleaned_text.strip()

    def _fallback_response(self, prompt: str) -> str:
        """Gera uma resposta de fallback quando a API do Ollama falha"""
        print("Usando modo de fallback para geração de resposta...")
        
        # Extrair a pergunta do prompt
        question_start = prompt.rfind("Pergunta:")
        if question_start > 0:
            question = prompt[question_start:].split("\n")[0].replace("Pergunta:", "").strip()
            detected_language = self._detect_language(question)
            
            # Pegar uma amostra do contexto para usar na resposta
            words = prompt.split()
            context_sample = " ".join(words[20:100]) if len(words) > 100 else " ".join(words)
            
            # Gerar resposta no idioma detectado
            if detected_language == "en":
                response = f"Based on the document text, {question}\n\n"
                response += f"Analyzing the PDF content, I found this relevant information: {context_sample}...\n\n"
                response += f"For a more accurate answer, make sure the Ollama service is running with the command 'ollama serve' and the DeepSeek model is installed with 'ollama pull deepseek-r1'."
            elif detected_language == "es":
                response = f"Según el texto del documento, {question}\n\n"
                response += f"Analizando el contenido del PDF, encontré esta información relevante: {context_sample}...\n\n"
                response += f"Para una respuesta más precisa, asegúrese de que el servicio Ollama esté ejecutándose con el comando 'ollama serve' y que el modelo DeepSeek esté instalado con 'ollama pull deepseek-r1'."
            else:  # Default para português
                response = f"Com base no texto do documento, {question}\n\n"
                response += f"Analisando o conteúdo do PDF, encontrei estas informações relevantes: {context_sample}...\n\n"
                response += f"Para responder com mais precisão, certifique-se de que o serviço Ollama está em execução com o comando 'ollama serve' e que o modelo DeepSeek está instalado com 'ollama pull deepseek-r1'."
        else:
            # Se não conseguir extrair a pergunta, retorna resposta padrão em português
            words = prompt.split()
            context_sample = " ".join(words[20:100]) if len(words) > 100 else " ".join(words)
            response = f"Baseado na análise do documento, encontrei: {context_sample}...\n\n"
            response += "Para uma análise detalhada com a IA, certifique-se de que o Ollama está em execução."
            
        return response

    def add_to_history(self, question: str, answer: str):
        """Adiciona uma interação ao histórico de conversa"""
        self.conversation_history.append({"question": question, "answer": answer})
        # Limitar o tamanho do histórico
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]

    def format_history(self) -> str:
        """Formata o histórico de conversa para inclusão no prompt"""
        if not self.conversation_history:
            return ""
            
        history_text = "Histórico de conversa:\n"
        for exchange in self.conversation_history:
            history_text += f"Pergunta: {exchange['question']}\n"
            history_text += f"Resposta: {exchange['answer']}\n\n"
            
        return history_text

    def is_index_ready(self) -> bool:
        """Verifica se o índice FAISS está pronto para uso"""
        return self.index is not None and len(self.text_chunks) > 0

    def truncate_context(self, text: str) -> str:
        """Limita o tamanho do contexto para não sobrecarregar o modelo"""
        if len(text) > self.max_context_length:
            return text[:self.max_context_length] + "..."
        return text