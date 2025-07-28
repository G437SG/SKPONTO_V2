#!/usr/bin/env python3
"""
Sistema de Backup de Segurança - SKPONTO V2
Backup local antes de testar em produção
"""

import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
import json

def create_backup():
    """Cria backup completo do sistema"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_security_{timestamp}"
    
    print(f"🔄 CRIANDO BACKUP DE SEGURANÇA")
    print(f"📁 Diretório: {backup_dir}")
    print("=" * 50)
    
    try:
        # Criar diretório de backup
        os.makedirs(backup_dir, exist_ok=True)
        
        # 1. Backup do banco SQLite local (se existir)
        sqlite_path = "instance/skponto.db"
        if os.path.exists(sqlite_path):
            shutil.copy2(sqlite_path, f"{backup_dir}/skponto_local.db")
            print(f"✅ SQLite backup: {sqlite_path}")
        else:
            print(f"⚠️ SQLite não encontrado: {sqlite_path}")
        
        # 2. Backup dos arquivos de configuração críticos
        critical_files = [
            "config.py",
            "app.py", 
            "requirements.txt",
            "runtime.txt",
            "Procfile"
        ]
        
        config_backup = f"{backup_dir}/config"
        os.makedirs(config_backup, exist_ok=True)
        
        for file in critical_files:
            if os.path.exists(file):
                shutil.copy2(file, f"{config_backup}/{file}")
                print(f"✅ Config backup: {file}")
        
        # 3. Backup dos modelos e rotas principais
        app_backup = f"{backup_dir}/app_code"
        if os.path.exists("app"):
            shutil.copytree("app", app_backup, dirs_exist_ok=True)
            print(f"✅ App code backup: app/")
        
        # 4. Backup dos logs de teste recentes
        log_files = [f for f in os.listdir(".") if f.startswith("test_") and f.endswith(".py")]
        if log_files:
            log_backup = f"{backup_dir}/test_logs"
            os.makedirs(log_backup, exist_ok=True)
            
            for log_file in log_files[-10:]:  # Últimos 10 arquivos de teste
                shutil.copy2(log_file, f"{log_backup}/{log_file}")
            print(f"✅ Test logs backup: {len(log_files)} arquivos")
        
        # 5. Informações do sistema
        system_info = {
            "backup_timestamp": timestamp,
            "python_version": subprocess.check_output(["python", "--version"], text=True).strip(),
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
            "directory_size": get_directory_size("."),
            "files_count": len([f for f in os.listdir(".") if os.path.isfile(f)])
        }
        
        with open(f"{backup_dir}/system_info.json", "w", encoding="utf-8") as f:
            json.dump(system_info, f, indent=2, ensure_ascii=False)
        
        print(f"✅ System info backup: system_info.json")
        
        # 6. Resumo do backup
        backup_size = get_directory_size(backup_dir)
        print("\n" + "=" * 50)
        print(f"🎉 BACKUP CONCLUÍDO COM SUCESSO!")
        print(f"📁 Diretório: {backup_dir}")
        print(f"💾 Tamanho: {backup_size:.2f} MB")
        print(f"⏰ Timestamp: {timestamp}")
        print(f"🔧 Git Commit: {system_info['git_commit'][:8]}")
        print("=" * 50)
        
        return backup_dir
        
    except Exception as e:
        print(f"❌ ERRO NO BACKUP: {str(e)}")
        return None

def get_directory_size(directory):
    """Calcula tamanho do diretório em MB"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB
    except:
        return 0

if __name__ == "__main__":
    print("🛡️ SISTEMA DE BACKUP DE SEGURANÇA - SKPONTO V2")
    print("=" * 60)
    
    backup_path = create_backup()
    
    if backup_path:
        print(f"\n✅ Backup disponível em: {backup_path}")
        print(f"🔄 Sistema pronto para testes em produção!")
    else:
        print(f"\n❌ Falha no backup - Verifique permissões")
