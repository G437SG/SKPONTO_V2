#!/usr/bin/env python3
"""
Script para resolver problemas de pip e dependências
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description=""):
    """Executar comando e retornar resultado"""
    print(f"🔧 {description}")
    print(f"   $ {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ Sucesso: {description}")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Erro: {description}")
            if result.stderr.strip():
                print(f"   ERRO: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: {description}")
        return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def check_python_environment():
    """Verificar ambiente Python"""
    print("🐍 VERIFICANDO AMBIENTE PYTHON...")
    
    # Verificar versão do Python
    run_command("python --version", "Verificando versão do Python")
    
    # Verificar pip
    run_command("pip --version", "Verificando versão do pip")
    
    # Verificar setuptools e wheel
    run_command("pip show setuptools", "Verificando setuptools")
    run_command("pip show wheel", "Verificando wheel")

def upgrade_pip_tools():
    """Atualizar ferramentas básicas do pip"""
    print("\n🔄 ATUALIZANDO FERRAMENTAS DO PIP...")
    
    commands = [
        ("python -m pip install --upgrade pip", "Atualizando pip"),
        ("pip install --upgrade setuptools", "Atualizando setuptools"),
        ("pip install --upgrade wheel", "Atualizando wheel"),
        ("pip install --upgrade build", "Instalando build tools")
    ]
    
    for command, description in commands:
        run_command(command, description)

def clear_pip_cache():
    """Limpar cache do pip"""
    print("\n🧹 LIMPANDO CACHE DO PIP...")
    
    commands = [
        ("pip cache purge", "Limpando cache do pip"),
        ("pip cache dir", "Verificando diretório de cache")
    ]
    
    for command, description in commands:
        run_command(command, description)

def check_requirements():
    """Verificar e reparar requirements.txt"""
    print("\n📋 VERIFICANDO REQUIREMENTS.TXT...")
    
    requirements_path = "requirements.txt"
    
    if not os.path.exists(requirements_path):
        print("⚠️ requirements.txt não encontrado")
        return False
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📄 Encontradas {len(lines)} dependências")
        
        # Verificar se há linhas problemáticas
        problematic_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('#'):
                # Verificar formato básico
                if '==' not in line and '>=' not in line and '~=' not in line and not line.replace('-', '').replace('_', '').replace('.', '').isalnum():
                    problematic_lines.append((i+1, line))
        
        if problematic_lines:
            print("⚠️ Linhas potencialmente problemáticas encontradas:")
            for line_num, line in problematic_lines:
                print(f"   Linha {line_num}: {line}")
        else:
            print("✅ requirements.txt parece estar bem formatado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao ler requirements.txt: {e}")
        return False

def install_dependencies_individually():
    """Instalar dependências uma por uma para identificar problemas"""
    print("\n📦 INSTALANDO DEPENDÊNCIAS INDIVIDUALMENTE...")
    
    requirements_path = "requirements.txt"
    
    if not os.path.exists(requirements_path):
        print("⚠️ requirements.txt não encontrado")
        return False
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        failed_packages = []
        success_count = 0
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                success = run_command(f"pip install {line}", f"Instalando {line}")
                if success:
                    success_count += 1
                else:
                    failed_packages.append(line)
        
        print(f"\n📊 RESULTADO:")
        print(f"✅ Instalados com sucesso: {success_count}")
        print(f"❌ Falharam: {len(failed_packages)}")
        
        if failed_packages:
            print(f"\n❌ Pacotes que falharam:")
            for package in failed_packages:
                print(f"   - {package}")
        
        return len(failed_packages) == 0
        
    except Exception as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def try_alternative_installation():
    """Tentar métodos alternativos de instalação"""
    print("\n🔄 TENTANDO MÉTODOS ALTERNATIVOS...")
    
    alternatives = [
        ("pip install -r requirements.txt --no-cache-dir", "Instalação sem cache"),
        ("pip install -r requirements.txt --force-reinstall", "Reinstalação forçada"),
        ("pip install -r requirements.txt --no-deps", "Instalação sem dependências"),
        ("pip install -r requirements.txt --user", "Instalação local do usuário")
    ]
    
    for command, description in alternatives:
        print(f"\n🔄 Tentando: {description}")
        success = run_command(command, description)
        if success:
            print(f"✅ Sucesso com: {description}")
            return True
    
    return False

def check_installed_packages():
    """Verificar pacotes instalados"""
    print("\n📋 VERIFICANDO PACOTES INSTALADOS...")
    
    run_command("pip list", "Listando pacotes instalados")
    run_command("pip check", "Verificando conflitos de dependências")

def main():
    """Função principal"""
    print("🔧 RESOLVENDO PROBLEMAS DE PIP E DEPENDÊNCIAS...")
    print("=" * 60)
    
    # 1. Verificar ambiente Python
    check_python_environment()
    
    # 2. Atualizar ferramentas do pip
    upgrade_pip_tools()
    
    # 3. Limpar cache
    clear_pip_cache()
    
    # 4. Verificar requirements.txt
    check_requirements()
    
    # 5. Tentar instalação normal primeiro
    print("\n📦 TENTANDO INSTALAÇÃO NORMAL...")
    normal_install = run_command("pip install -r requirements.txt", "Instalação normal")
    
    if not normal_install:
        print("\n⚠️ Instalação normal falhou, tentando alternativas...")
        
        # 6. Instalar individualmente
        individual_success = install_dependencies_individually()
        
        if not individual_success:
            # 7. Tentar métodos alternativos
            alternative_success = try_alternative_installation()
            
            if not alternative_success:
                print("\n❌ TODAS AS TENTATIVAS FALHARAM")
                print("💡 SUGESTÕES:")
                print("   1. Verifique se há conflitos no requirements.txt")
                print("   2. Considere usar um ambiente virtual limpo")
                print("   3. Verifique se há problemas de rede")
                print("   4. Considere atualizar o Python")
                return False
    
    # 8. Verificar resultado final
    check_installed_packages()
    
    print("\n✅ RESOLUÇÃO DE PROBLEMAS DE PIP CONCLUÍDA!")
    print("🚀 Agora você pode tentar instalar pacotes normalmente")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
