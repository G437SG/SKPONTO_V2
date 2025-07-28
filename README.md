# 🕐 SKPONTO V2 - Sistema Completo de Controle de Ponto

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)
![Bootstrap](https://img.shields.io/badge/bootstrap-5.0+-purple.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-13+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-red.svg)

Sistema completo de controle de ponto desenvolvido em Flask com interface moderna e funcionalidades avançadas de gestão de pessoal. **Atualizado em 28/07/2025 - Correções críticas de integridade de dados aplicadas.**

## 🚀 Funcionalidades Principais

### 👥 Gestão de Usuários
- **Sistema de autenticação multi-nível** (Admin, Trabalhador, Estagiário)
- **Aprovação de usuários** com fluxo administrativo
- **Perfis personalizados** com upload de foto
- **Logs de segurança** e auditoria completa

### ⏰ Controle de Ponto
- **Entrada/saída automatizada** com timestamp
- **Cálculo automático de horas** trabalhadas
- **Controle de horários** com validações
- **Relatórios detalhados** em PDF e Excel

### 🏥 Sistema de Atestados
- **Upload seguro** de documentos médicos
- **Armazenamento local** seguro
- **Gestão administrativa** de atestados
- **Validação e aprovação** de documentos

### 📊 Dashboards e Relatórios
- **Dashboards interativos** com gráficos
- **Estatísticas em tempo real** de performance
- **Relatórios customizáveis** por período
- **Exportação** em múltiplos formatos

### 🔔 Sistema de Notificações
- **Notificações em tempo real** com dropdown
- **Truncamento inteligente** de texto longo
- **Histórico completo** de notificações
- **Marcação automática** como lida

### 💾 Backup Automático ✅ **OPERACIONAL**
- **Sistema totalmente funcional** com backup automático a cada 24 horas
- **Agendador com threading** para execução em background
- **Armazenamento local** totalmente independente
- **Dashboard administrativo** com monitoramento em tempo real
- **Histórico completo** de backups com estatísticas
- **Backup manual** sob demanda
- **Retenção configurável** (30 dias por padrão)
- **Status em tempo real** - ATIVO ✅

## 🎯 **CORREÇÕES IMPLEMENTADAS - VERSÃO 2.0**

### ✅ **PROBLEMA RESOLVIDO: Backup Automático Inativo**
- **Situação anterior:** Backup automático aparecia como "inativo" no dashboard
- **Causa identificada:** Configuração `AUTO_BACKUP_ENABLED` não estava definida
- **Solução implementada:** 
  - Adicionada configuração completa no `config.py`
  - Criado serviço `backup_scheduler.py` com threading
  - Implementado monitoramento em tempo real
  - Dashboard atualizado com status operacional

### 🔧 **MELHORIAS TÉCNICAS IMPLEMENTADAS**
- **Configuração centralizada:** Todas as configurações de backup no `config.py`
- **Agendador otimizado:** Sistema de threads para execução em background
- **Armazenamento local:** Independência do Dropbox para maior confiabilidade
- **Interface consolidada:** Dashboard administrativo unificado
- **Logs aprimorados:** Sistema de auditoria completo

### 📈 **STATUS ATUAL DO SISTEMA**
- ✅ **Backup Automático:** ATIVO - Executando a cada 24 horas
- ✅ **Armazenamento Local:** Funcionando perfeitamente
- ✅ **Dashboard Admin:** Consolidado e responsivo
- ✅ **Configurações:** Centralizadas e funcionais
- ✅ **Monitoramento:** Em tempo real com estatísticas

### 💾 Backup Automático ✅ **OPERACIONAL**
- **Sistema totalmente funcional** com backup automático a cada 24 horas
- **Agendador com threading** para execução em background
- **Armazenamento local** totalmente independente
- **Dashboard administrativo** com monitoramento em tempo real
- **Histórico completo** de backups com estatísticas
- **Backup manual** sob demanda
- **Retenção configurável** (30 dias por padrão)
- **Status em tempo real** - ATIVO ✅

## 🛠️ Tecnologias Utilizadas

### Backend
- **Flask 2.3+** - Framework web principal
- **SQLAlchemy** - ORM para gerenciamento de banco
- **Flask-Login** - Sistema de autenticação
- **Flask-WTF** - Formulários e validação CSRF
- **Flask-Migrate** - Migrações de banco de dados
- **Werkzeug** - Utilitários web e segurança

### Frontend
- **Bootstrap 5** - Framework CSS responsivo
- **jQuery** - Manipulação DOM e AJAX
- **Chart.js** - Gráficos interativos
- **Font Awesome** - Ícones
- **DataTables** - Tabelas avançadas

### Banco de Dados
- **SQLite** - Desenvolvimento e produção simples
- **PostgreSQL** - Produção (opcionalmente)

### Segurança
- **bcrypt** - Hash de senhas
- **CSRF Protection** - Proteção contra ataques
- **Rate Limiting** - Controle de tentativas
- **Secure Headers** - Cabeçalhos de segurança

## 📋 Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes)
- Git

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/G437SG/SKPONTO_.git
cd SKPONTO_
```

### 2. Crie um ambiente virtual
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

Edite o arquivo `.env` com suas configurações:
```env
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=sqlite:///skponto.db
```

### 5. Inicialize o banco de dados
```bash
flask db upgrade
python -c "from app import create_app; from app.models import *; app = create_app(); app.app_context().push(); db.create_all()"
```

### 6. Crie o usuário administrador (opcional)
```bash
python create_test_admin.py
```

### 7. Execute a aplicação
```bash
python app.py
```

A aplicação estará disponível em: `http://localhost:5000`

## 🎯 **VERIFICAÇÃO DO SISTEMA DE BACKUP**

### Validar se o backup está funcionando:
```bash
# Verificar status do backup automático
python test_backup_system.py

# Verificar configurações
python -c "from app import create_app; app = create_app(); print(f'Backup Automático: {app.config.get(\"AUTO_BACKUP_ENABLED\")}')"
```

### Resultado esperado:
```
✅ Backup Automático: ATIVO
✅ Frequência: 24 horas
✅ Retenção: 30 dias
✅ Status: OPERACIONAL
```

## 👤 Acesso Inicial

### Administrador Padrão
- **Email:** admin@skponto.com
- **Senha:** admin123

⚠️ **Importante:** Altere a senha do administrador após o primeiro login!

## 🎯 Como Usar

### 1. Primeiro Acesso
1. Acesse a aplicação em `http://localhost:5000`
2. Faça login com as credenciais do administrador
3. Configure o sistema de backup em **Admin > Backup**
4. Crie usuários em **Admin > Usuários**

### 2. Usuários Comuns
1. Solicite conta através do formulário de registro
2. Aguarde aprovação do administrador
3. Faça login e registre seu ponto
4. Envie atestados quando necessário

### 3. Administradores
1. Aprovem novos usuários
2. Monitorem o sistema através do dashboard
3. Gerenciem atestados e relatórios
4. **Monitorem backups automáticos** em tempo real
5. Configurem parâmetros de backup
6. Executem backups manuais quando necessário

## 💾 **SISTEMA DE BACKUP - GUIA COMPLETO**

### 📋 **Configuração Atual**
```python
# config.py - Configurações de backup
AUTO_BACKUP_ENABLED = True          # Backup automático habilitado
BACKUP_FREQUENCY_HOURS = 24         # Backup a cada 24 horas
BACKUP_RETENTION_DAYS = 30          # Manter backups por 30 dias
```

### 🔄 **Funcionamento**
1. **Backup automático:** Executa a cada 24 horas em background
2. **Armazenamento local:** Salva em `storage/backups/`
3. **Formato:** Arquivos ZIP com timestamp
4. **Conteúdo:** Banco de dados + arquivos importantes
5. **Monitoramento:** Dashboard com status em tempo real

### 🎛️ **Dashboard de Backup**
- **URL:** `/admin/backup/dashboard`
- **Funcionalidades:**
  - Status do backup automático
  - Histórico completo de backups
  - Estatísticas de armazenamento
  - Backup manual sob demanda
  - Configurações avançadas

### 📊 **Monitoramento**
```bash
# Verificar status
python test_backup_system.py

# Executar backup manual
python -c "from backup_scheduler import backup_scheduler; backup_scheduler.run_manual_backup(1)"
```

## 🔒 Segurança

### Recursos Implementados
- ✅ Autenticação segura com bcrypt
- ✅ Proteção CSRF em todos os formulários
- ✅ Validação de entrada rigorosa
- ✅ Rate limiting para prevenir ataques
- ✅ Logs de segurança detalhados
- ✅ Sessões seguras com cookies HTTPOnly
- ✅ Sanitização de uploads de arquivo

### Recomendações
- Use HTTPS em produção
- Configure firewall adequadamente
- Monitore logs regularmente
- Mantenha backups atualizados
- Atualize dependências regularmente

## 🚀 Deploy

### Opções de Deploy
- **Render** (recomendado)
- **Heroku**
- **PythonAnywhere**
- **VPS próprio**

### Configuração para Produção
1. Configure variáveis de ambiente
2. Use banco PostgreSQL
3. Configure domínio e SSL
4. Habilite compressão GZIP
5. Configure monitoramento

## 📝 Documentação

### Arquivos de Documentação
- `RELATORIO_CORRECOES_FINAIS.md` - Correções implementadas
- `RELATORIO_LAYOUT_NOTIFICACOES.md` - Sistema de notificações
- `RELATORIO_OTIMIZACOES.md` - Otimizações realizadas
- `DEPLOY_RENDER.md` - Guia de deploy

### Estrutura do Projeto
```
SKPONTO_V2/
├── app/
│   ├── admin/          # Rotas administrativas
│   ├── api/            # API REST
│   ├── auth/           # Autenticação
│   ├── main/           # Rotas principais
│   ├── static/         # Arquivos estáticos
│   ├── templates/      # Templates HTML
│   └── models.py       # Modelos do banco
├── storage/            # Armazenamento local
│   ├── backups/        # Backups automáticos ✅
│   └── uploads/        # Arquivos enviados
├── migrations/         # Migrações do banco
├── backup_scheduler.py # Sistema de backup ✅
├── requirements.txt    # Dependências
├── config.py          # Configurações ✅
├── app.py             # Aplicação principal
└── wsgi.py            # Entry point WSGI
```

## 🔧 **ARQUIVOS DE BACKUP IMPORTANTES**

### 📄 **Novos Arquivos Implementados**
- `backup_scheduler.py` - **Sistema de agendamento de backup**
- `test_backup_system.py` - **Validação do sistema de backup**
- `storage/backups/` - **Diretório de armazenamento local**

### 📋 **Modificações Realizadas**
- `config.py` - **Configurações de backup adicionadas**
- `app/admin/backup_dashboard.py` - **Dashboard atualizado**
- `app/__init__.py` - **Inicialização do backup scheduler**

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🐛 Bugs e Sugestões

- Abra uma [issue](https://github.com/G437SG/SKPONTO_/issues) para reportar bugs
- Sugira melhorias através de [pull requests](https://github.com/G437SG/SKPONTO_/pulls)

## 📞 Contato

- **GitHub:** [@G437SG](https://github.com/G437SG)
- **Email:** Através do GitHub

## 🎉 Agradecimentos

Obrigado por usar o SKPONTO V2! Este sistema foi desenvolvido com muito carinho para facilitar a gestão de controle de ponto em empresas de todos os tamanhos.

## 📈 **STATUS ATUAL DO SISTEMA**

### ✅ **SISTEMA 100% OPERACIONAL**
- **Backup Automático:** ATIVO - Executando a cada 24 horas
- **Controle de Ponto:** FUNCIONANDO
- **Gestão de Usuários:** OPERACIONAL
- **Sistema de Atestados:** INTEGRADO
- **Dashboard Admin:** CONSOLIDADO
- **Segurança:** IMPLEMENTADA
- **Monitoramento:** ATIVO

### 🔄 **ÚLTIMA ATUALIZAÇÃO**
- **Data:** Janeiro 2025
- **Versão:** 2.0
- **Principais melhorias:**
  - ✅ Backup automático totalmente funcional
  - ✅ Sistema de armazenamento local implementado
  - ✅ Dashboard administrativo consolidado
  - ✅ Configurações centralizadas
  - ✅ Monitoramento em tempo real

### 🚀 **PRÓXIMOS PASSOS**
1. Validar sistema em produção
2. Implementar melhorias de performance
3. Adicionar funcionalidades extras
4. Manter sistema atualizado

---

⭐ **Se este projeto te ajudou, não esqueça de dar uma estrela!** ⭐

**🎯 BACKUP AUTOMÁTICO: PROBLEMA RESOLVIDO E SISTEMA OPERACIONAL!** 🎯
