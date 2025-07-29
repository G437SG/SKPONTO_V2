#!/usr/bin/env python3
"""
Debug Erro 500 - SKPONTO V2
"""

import requests

def check_500_error():
    base_url = "https://skponto.onrender.com"
    
    print("🚨 VERIFICANDO ERRO 500 - SKPONTO V2")
    print("=" * 50)
    
    pages = [
        "/",
        "/login", 
        "/admin/usuarios",
        "/api/status"
    ]
    
    for page in pages:
        try:
            print(f"\n🔍 Testando: {page}")
            response = requests.get(base_url + page, timeout=15)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 500:
                print("❌ ERRO 500 DETECTADO!")
                print(f"Headers: {dict(response.headers)}")
                print(f"Content preview: {response.text[:500]}...")
            elif response.status_code == 200:
                print("✅ OK")
            elif response.status_code == 302:
                print(f"🔄 REDIRECT → {response.headers.get('Location')}")
            else:
                print(f"❓ Status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏳ TIMEOUT")
        except requests.exceptions.ConnectionError:
            print("🔌 CONNECTION ERROR")
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    check_500_error()
