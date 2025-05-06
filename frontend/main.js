class ChatApp {
    constructor() {
        // Elementos principais
        this.uploadArea = document.getElementById('upload-area');
        this.chatMessages = document.getElementById('chat-messages');
        this.inputArea = document.getElementById('input-area');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.uploadButton = document.getElementById('upload-button');
        this.pdfInput = document.getElementById('pdf-input');

        // Elementos de navegação
        this.navButtons = document.querySelectorAll('.nav-button');
        this.sections = document.querySelectorAll('.section');

        // Elementos de tema
        this.themeToggle = document.querySelector('.theme-toggle');
        this.body = document.body;

        // Estado
        this.isPdfUploaded = false;
        this.isDarkMode = true;

        // Elementos de loading
        this.loadingContainer = null;
        this.progressBar = null;
        this.progressFill = null;

        this.initializeEventListeners();
        this.loadThemePreference();
        this.initializeAnimations();
    }

    initializeAnimations() {
        // Garante que as animações só comecem após o carregamento completo da página
        window.addEventListener('load', () => {
            document.body.classList.add('loaded');
        });
    }

    initializeEventListeners() {
        // Upload de PDF
        this.uploadButton.addEventListener('click', () => this.pdfInput.click());
        this.pdfInput.addEventListener('change', (e) => this.handlePdfUpload(e));

        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('drag-over');
        });

        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('drag-over');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                this.pdfInput.files = e.dataTransfer.files;
                this.handlePdfUpload({ target: this.pdfInput });
            }
        });

        // Envio de mensagens
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        this.sendButton.addEventListener('click', () => this.sendMessage());

        // Navegação
        this.navButtons.forEach(button => {
            button.addEventListener('click', () => this.handleNavigation(button));
        });

        // Tema
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    loadThemePreference() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            this.toggleTheme();
        }
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        this.body.classList.toggle('light-mode');
        this.themeToggle.innerHTML = this.isDarkMode ?
            '<i class="fas fa-moon"></i>' :
            '<i class="fas fa-sun"></i>';
        localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
    }

    handleNavigation(button) {
        // Atualiza botões ativos
        this.navButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // Atualiza seções visíveis
        const targetSection = button.dataset.section;
        this.sections.forEach(section => {
            section.classList.remove('active');
            if (section.id === targetSection) {
                section.classList.add('active');
            }
        });
    }

    createLoadingElements() {
        this.loadingContainer = document.createElement('div');
        this.loadingContainer.className = 'loading-container';

        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';

        this.progressBar = document.createElement('div');
        this.progressBar.className = 'progress-bar';

        this.progressFill = document.createElement('div');
        this.progressFill.className = 'progress-fill';

        this.progressBar.appendChild(this.progressFill);
        this.loadingContainer.appendChild(spinner);
        this.loadingContainer.appendChild(this.progressBar);
    }

    updateProgress(progress) {
        if (this.progressFill) {
            this.progressFill.style.width = `${progress}%`;
        }
    }

    async handlePdfUpload(event) {
        const file = event.target.files[0];
        if (!file || file.type !== 'application/pdf') {
            this.addMessage('Sistema', 'Por favor, selecione um arquivo PDF válido.', 'bot');
            return;
        }

        // Cria e mostra elementos de loading
        this.createLoadingElements();
        this.uploadButton.innerHTML = '';
        this.uploadButton.appendChild(this.loadingContainer);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const xhr = new XMLHttpRequest();

            // Configura o evento de progresso
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const progress = (e.loaded / e.total) * 100;
                    this.updateProgress(progress);
                }
            });

            // Configura o evento de conclusão
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    const data = JSON.parse(xhr.responseText);
                    this.isPdfUploaded = true;
                    this.uploadArea.style.display = 'none';
                    this.chatMessages.style.display = 'block';
                    this.inputArea.style.display = 'flex';
                    this.messageInput.disabled = false;
                    this.sendButton.disabled = false;
                    this.addMessage('Sistema', data.statistics, 'bot');
                } else {
                    const data = JSON.parse(xhr.responseText);
                    this.addMessage('Sistema', 'Erro ao processar o PDF: ' + data.error, 'bot');
                }
            });

            // Configura o evento de erro
            xhr.addEventListener('error', () => {
                this.addMessage('Sistema', 'Erro ao enviar o arquivo', 'bot');
            });

            // Inicia o upload
            xhr.open('POST', 'http://localhost:8000/upload-pdf');
            xhr.send(formData);

        } catch (error) {
            this.addMessage('Sistema', 'Erro ao enviar o arquivo: ' + error.message, 'bot');
        } finally {
            // Restaura botão
            this.uploadButton.disabled = false;
            this.uploadButton.innerHTML = 'Escolher arquivo PDF';
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Adiciona mensagem do usuário
        this.addMessage('Você', message, 'user');
        this.messageInput.value = '';

        // Mostra loading
        this.sendButton.disabled = true;
        this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            // Adicionar indicador de digitação
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot-message typing';
            typingDiv.innerHTML = '<strong>Assistente:</strong><p>Analisando o documento...</p>';
            this.chatMessages.appendChild(typingDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            // Remover indicador de digitação
            this.chatMessages.removeChild(typingDiv);

            if (data.success) {
                this.addMessage('Assistente', data.response, 'bot');
            } else {
                // Tratar erro na resposta
                this.addMessage('Sistema', data.response || 'Ocorreu um erro ao processar sua pergunta.', 'bot');
            }
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            this.addMessage('Sistema', 'Erro ao processar sua mensagem: ' + error.message, 'bot');
        } finally {
            // Restaura botão
            this.sendButton.disabled = false;
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }

    addMessage(sender, text, type) {
        if (!text) {
            text = "Sem resposta disponível.";
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        // Escapar HTML e transformar quebras de linha em <br>
        let formattedText = text;

        // Verifica se o texto contém marcação Markdown e preserva quebras de linha
        if (text.includes('**') || text.includes('- ')) {
            // Converter markdown para HTML
            formattedText = this.markdownToHtml(text);
        } else {
            // Substituir quebras de linha por <br> em texto normal
            formattedText = text.replace(/\n/g, '<br>');
        }

        // Criar o HTML da mensagem
        messageDiv.innerHTML = `
            <strong>${sender}:</strong>
            <p>${formattedText}</p>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    // Converter markdown simples para HTML
    markdownToHtml(text) {
        // Substituir quebras de linha por <br>
        let html = text.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

        // Converter **texto** para <strong>texto</strong>
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Converter listas com traço
        html = html.replace(/- (.*?)(<br|$)/g, '• $1$2');

        return html;
    }
}

// Inicializa o app
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});