"""
pdf_processor.py - Processador de documentos PDF

Este módulo é responsável por todas as operações relacionadas ao processamento de PDFs:
1. Extração de texto e metadados de documentos PDF
2. Análise e detecção do idioma do conteúdo
3. Segmentação do texto em páginas/chunks para processamento
4. Cálculo de estatísticas sobre o documento (páginas, palavras, etc.)
5. Preparação dos dados para indexação vetorial

Utiliza várias bibliotecas para processamento de PDF, incluindo PyPDF2 e pdfminer,
permitindo a extração eficiente de conteúdo mesmo de PDFs complexos.
"""

import pdfplumber
import logging
import re
from typing import Dict, List, Optional
import concurrent.futures
from functools import lru_cache
from langdetect import detect, LangDetectException
import math # Adicionado para math.ceil
from concurrent.futures import ThreadPoolExecutor
import time

# Configurar logging
logging.getLogger("pdfminer").setLevel(logging.WARNING)
# Configurar logging langdetect
logging.getLogger('langdetect').setLevel(logging.WARNING)


class PDFProcessor:
    def __init__(self):
        self.pages = []
        self.pdf_loaded = False
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.total_words = 0
        self.detected_language = "N/A" # Novo atributo

    @lru_cache(maxsize=100)
    def clean_text(self, text: Optional[str]) -> str: # Adicionado Optional
        """Limpa o texto extraído"""
        if not text:
            return ""
        # Remover caracteres especiais e espaços extras
        text = re.sub(r'\s+', ' ', text)
        # Remover caracteres não imprimíveis
        text = ''.join(char for char in text if char.isprintable())
        return text.strip()

    def process_pdf(self, file_path: str):
        """Lê e extrai texto de um PDF usando pdfplumber"""
        print("Iniciando processamento do PDF...")
        self.pages = []
        self.pdf_loaded = False
        
        try:
            # Suprime avisos específicos do pdfplumber
            logging.getLogger('pdfminer').setLevel(logging.ERROR)
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"Total de páginas encontradas: {total_pages}")
                
                # Processar páginas em paralelo
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    for i, page in enumerate(pdf.pages):
                        futures.append(
                            executor.submit(self._process_page, page, i + 1)
                        )
                    
                    # Coletar resultados
                    for future in futures:
                        try:
                            result = future.result()
                            if result:
                                self.pages.append(result)
                        except Exception as e:
                            print(f"Erro ao processar página: {str(e)}")
                            continue

            if not self.pages:
                print("Nenhuma página foi processada com sucesso.")
                return False, "Nenhuma página foi processada com sucesso.", []

            self.pdf_loaded = True
            print(f"PDF processado com sucesso. {len(self.pages)} páginas processadas.")
            return True, "PDF processado com sucesso!", self.pages

        except Exception as e:
            print(f"Erro ao processar PDF: {str(e)}")
            self.pdf_loaded = False
            return False, f"Erro ao processar PDF: {str(e)}", []

    def _process_page(self, page, page_number):
        """Processa uma única página do PDF"""
        try:
            # Garante que está usando a MediaBox
            page.bbox = page.mediabox
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            
            # Tenta extrair texto com configurações alternativas se estiver vazio
            if not text or len(text.strip()) < 10:
                try:
                    # Tentar com configurações diferentes
                    text = page.extract_text(x_tolerance=5, y_tolerance=10)
                except:
                    pass
                    
            if text:
                # Limpar o texto para melhorar a qualidade
                text = self.clean_text(text)
                words = text.split()
                
                return {
                    "number": page_number,
                    "content": text,
                    "word_count": len(words),
                    "extracted_success": True
                }
            return None
        except Exception as e:
            print(f"Erro ao processar página {page_number}: {str(e)}")
            return None

    def is_loaded(self):
        """Retorna True se o PDF foi carregado corretamente."""
        return self.pdf_loaded

    def get_pages_for_indexing(self):
        """Retorna o conteúdo das páginas para indexação"""
        if not self.pages:
            print("Nenhuma página disponível para indexação.")
            return []
            
        try:
            return [{"content": page["content"]} for page in self.pages if "content" in page]
        except Exception as e:
            print(f"Erro ao preparar páginas para indexação: {str(e)}")
            # Fallback para formato simplificado
            return [page.get("content", "") for page in self.pages if page.get("content")]

    def get_statistics(self):
        """Retorna estatísticas do PDF processado"""
        if not self.pages:
            return {
                "success": False,
                "message": "Nenhum conteúdo extraído.",
                "total_pages": 0,
                "processed_pages": 0,
                "total_words": 0,
                "average_words_per_page": 0,
                "language": "N/A"
            }
        
        total_pages = len(self.pages)
        total_words = sum(page["word_count"] for page in self.pages)
        average_words = total_words / total_pages if total_pages > 0 else 0
        
        return {
            "success": True,
            "message": "Estatísticas calculadas com sucesso",
            "total_pages": total_pages,
            "processed_pages": total_pages,
            "total_words": total_words,
            "average_words_per_page": average_words,
            "language": "pt"  # Assumindo português por padrão
        }

    def detect_language(self) -> str:
        """Detecta o idioma principal do texto extraído."""
        if not self.pages:
            return "N/A"

        # Usar uma amostra do texto para detecção (primeiras N páginas ou M caracteres)
        sample_text = " ".join(p["content"] for p in self.pages[:5]) # Amostra das 5 primeiras páginas
        sample_text = sample_text[:2000] # Limitar a 2000 caracteres

        if not sample_text:
             return "N/A"

        try:
            lang = detect(sample_text)
            print(f"Idioma detectado: {lang}")
            return lang
        except LangDetectException:
            print("Não foi possível detectar o idioma.")
            return "N/A"
        except Exception as e:
            print(f"Erro na detecção de idioma: {e}")
            return "N/A"

    def __del__(self):
        """Cleanup ao destruir a instância"""
        if self._executor:
            self._executor.shutdown(wait=True)
            print("Recurso Executor liberado.")

# Remover get_summary e outros métodos não utilizados se houver
