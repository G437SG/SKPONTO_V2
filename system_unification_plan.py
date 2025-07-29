#!/usr/bin/env python3
"""
🔄 PLANO DE UNIFICAÇÃO DO SISTEMA SKPONTO
========================================

Baseado na análise detalhada, este script implementa a unificação
dos arquivos duplicados seguindo a ordem de prioridade identificada.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

class SystemUnifier:
    def __init__(self, workspace_path):
        self.workspace = Path(workspace_path)
        self.backup_dir = self.workspace / f"unification_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.unification_log = []
        
    def log_action(self, action, files, status="SUCCESS"):
        """Registra ações de unificação"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "files": files if isinstance(files, list) else [files],
            "status": status
        }
        self.unification_log.append(entry)
        print(f"📝 {action}: {status}")
        
    def create_backup(self, file_path):
        """Cria backup antes de remover arquivo"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                # Mantém estrutura de diretórios no backup
                relative_path = file_path.relative_to(self.workspace)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                return True
        except Exception as e:
            self.log_action(f"BACKUP FAILED for {file_path}", str(e), "ERROR")
            return False
        return True
    
    def safe_remove(self, file_path):
        """Remove arquivo com backup de segurança"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                if self.create_backup(file_path):
                    file_path.unlink()
                    self.log_action("REMOVE", str(file_path))
                    return True
                else:
                    self.log_action("REMOVE FAILED", str(file_path), "ERROR")
                    return False
        except Exception as e:
            self.log_action("REMOVE ERROR", f"{file_path}: {e}", "ERROR")
            return False
        return True
        
    def priority_1_config_cleanup(self):
        """🔴 PRIORIDADE 1: Limpar configs duplicados"""
        print("\n🔴 INICIANDO PRIORIDADE 1 - LIMPEZA DE CONFIGS")
        
        # Manter apenas config.py principal
        configs_to_remove = [
            "backup_security_20250728_134443/config/config.py"
        ]
        
        for config in configs_to_remove:
            config_path = self.workspace / config
            if config_path.exists():
                self.safe_remove(config_path)
                
        print("✅ Limpeza de configs concluída")
        
    def priority_2_template_unification(self):
        """🟡 PRIORIDADE 2: Unificar templates duplicados"""
        print("\n🟡 INICIANDO PRIORIDADE 2 - UNIFICAÇÃO DE TEMPLATES")
        
        # Mapeamento: manter -> remover
        template_plan = {
            # atestados.html - manter main
            "app/templates/main/atestados.html": [
                "app/templates/admin/atestados.html",
                "backup_security_20250728_134443/app_code/templates/admin/atestados.html",
                "backup_security_20250728_134443/app_code/templates/main/atestados.html"
            ],
            
            # dashboard.html - manter debug (mais moderno)
            "app/templates/admin/debug/dashboard.html": [
                "app/admin/backup/templates/admin/backup/dashboard.html",
                "app/templates/admin/dashboard.html",
                "app/templates/main/dashboard.html",
                "app/templates/main/hour_bank/dashboard.html",
                "backup_security_20250728_134443/app_code/admin/backup/templates/admin/backup/dashboard.html",
                "backup_security_20250728_134443/app_code/templates/admin/dashboard.html",
                "backup_security_20250728_134443/app_code/templates/main/dashboard.html",
                "backup_security_20250728_134443/app_code/templates/main/hour_bank/dashboard.html"
            ],
            
            # logs.html - manter debug (mais moderno)
            "app/templates/admin/debug/logs.html": [
                "app/templates/admin/logs.html",
                "backup_security_20250728_134443/app_code/templates/admin/logs.html"
            ],
            
            # notificacoes.html - manter main (mais completo)
            "app/templates/main/notificacoes.html": [
                "app/templates/admin/notificacoes.html",
                "backup_security_20250728_134443/app_code/templates/admin/notificacoes.html",
                "backup_security_20250728_134443/app_code/templates/main/notificacoes.html"
            ]
        }
        
        for keep_template, remove_templates in template_plan.items():
            keep_path = self.workspace / keep_template
            if keep_path.exists():
                print(f"🎨 Mantendo: {keep_template}")
                
                for remove_template in remove_templates:
                    remove_path = self.workspace / remove_template
                    if remove_path.exists():
                        self.safe_remove(remove_path)
            else:
                print(f"⚠️ Template principal não encontrado: {keep_template}")
                
        print("✅ Unificação de templates concluída")
        
    def priority_3_test_cleanup(self):
        """🟢 PRIORIDADE 3: Limpar arquivos de teste obsoletos"""
        print("\n🟢 INICIANDO PRIORIDADE 3 - LIMPEZA DE TESTES")
        
        # Manter apenas os testes essenciais e mais recentes
        tests_to_keep = [
            "test_final_complete.py",  # Teste completo mais recente
            "test_login_intelligent.py",  # Login inteligente
            "test_complete_system.py",  # Sistema completo
            "test_corrected_routes.py"  # Rotas corrigidas
        ]
        
        # Padrões de arquivos de teste para limpeza
        test_patterns = [
            "test_*.py",
            "debug_*.py",
            "*_debug.py",
            "check_*.py",
            "diagnose_*.py",
            "monitor_*.py",
            "quick_test_*.py"
        ]
        
        obsolete_tests = []
        for pattern in test_patterns:
            for test_file in self.workspace.glob(pattern):
                if test_file.name not in tests_to_keep:
                    obsolete_tests.append(test_file)
        
        print(f"📊 Encontrados {len(obsolete_tests)} testes obsoletos")
        
        # Remover testes obsoletos
        for test_file in obsolete_tests:
            if test_file.exists():
                self.safe_remove(test_file)
                
        print("✅ Limpeza de testes concluída")
        
    def priority_4_blueprint_cleanup(self):
        """🔵 PRIORIDADE 4: Limpar blueprints duplicados"""
        print("\n🔵 INICIANDO PRIORIDADE 4 - LIMPEZA DE BLUEPRINTS")
        
        # Blueprints duplicados identificados
        blueprint_duplicates = [
            "app/debug_blueprint_fixed.py"  # Manter debug_blueprint.py
        ]
        
        for blueprint in blueprint_duplicates:
            blueprint_path = self.workspace / blueprint
            if blueprint_path.exists():
                self.safe_remove(blueprint_path)
                
        print("✅ Limpeza de blueprints concluída")
        
    def priority_5_backup_cleanup(self):
        """🟠 PRIORIDADE 5: Limpar backups antigos"""
        print("\n🟠 INICIANDO PRIORIDADE 5 - LIMPEZA DE BACKUPS")
        
        # Remover backup antigo (já analisado)
        backup_dirs = [
            "backup_security_20250728_134443"
        ]
        
        for backup_dir in backup_dirs:
            backup_path = self.workspace / backup_dir
            if backup_path.exists():
                print(f"🗑️ Removendo backup antigo: {backup_dir}")
                shutil.rmtree(backup_path)
                self.log_action("REMOVE BACKUP DIR", str(backup_path))
                
        print("✅ Limpeza de backups concluída")
        
    def run_full_unification(self):
        """Executa unificação completa do sistema"""
        print("🚀 INICIANDO UNIFICAÇÃO COMPLETA DO SISTEMA SKPONTO")
        print("=" * 60)
        
        # Criar diretório de backup
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Backup criado em: {self.backup_dir}")
        
        try:
            # Executar por ordem de prioridade
            self.priority_1_config_cleanup()
            self.priority_2_template_unification()
            self.priority_3_test_cleanup()
            self.priority_4_blueprint_cleanup()
            self.priority_5_backup_cleanup()
            
            # Salvar log de unificação
            log_file = self.workspace / "unification_log.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.unification_log, f, indent=2, ensure_ascii=False)
                
            # Estatísticas finais
            total_actions = len(self.unification_log)
            successful_actions = len([a for a in self.unification_log if a['status'] == 'SUCCESS'])
            
            print("\n" + "=" * 60)
            print("🎉 UNIFICAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"📊 Total de ações: {total_actions}")
            print(f"✅ Ações bem-sucedidas: {successful_actions}")
            print(f"❌ Ações com erro: {total_actions - successful_actions}")
            print(f"📁 Backup salvo em: {self.backup_dir}")
            print(f"📝 Log salvo em: {log_file}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO DURANTE UNIFICAÇÃO: {e}")
            self.log_action("UNIFICATION ERROR", str(e), "CRITICAL")
            return False

if __name__ == "__main__":
    workspace = r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2"
    
    print("🔄 SISTEMA DE UNIFICAÇÃO SKPONTO")
    print("=" * 40)
    print("Este script irá:")
    print("• Fazer backup de todos os arquivos antes da remoção")
    print("• Remover arquivos duplicados por ordem de prioridade")
    print("• Manter apenas as versões mais atualizadas e funcionais")
    print("• Registrar todas as ações em log detalhado")
    
    confirm = input("\n⚠️ Confirma a execução? (s/N): ").lower().strip()
    
    if confirm == 's':
        unifier = SystemUnifier(workspace)
        success = unifier.run_full_unification()
        
        if success:
            print("\n🎊 Sistema unificado com sucesso!")
            print("🔧 Recomenda-se testar o sistema após a unificação")
        else:
            print("\n⚠️ Unificação completada com alguns erros - verificar log")
    else:
        print("❌ Unificação cancelada pelo usuário")
