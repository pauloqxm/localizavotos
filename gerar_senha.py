#!/usr/bin/env python3
"""
Script para gerar hash de senha para o LocalizaVotos

Uso:
    python gerar_senha.py
"""

import hashlib

print("=" * 50)
print("🔐 GERADOR DE SENHA - LocalizaVotos")
print("=" * 50)
print()

# Solicitar senha
senha = input("Digite sua nova senha: ")
confirma = input("Confirme sua senha: ")

if senha != confirma:
    print("\n❌ ERRO: As senhas não coincidem!")
    exit(1)

if len(senha) < 6:
    print("\n⚠️  AVISO: Senha muito curta. Recomendamos pelo menos 6 caracteres.")
    continuar = input("Deseja continuar mesmo assim? (s/n): ")
    if continuar.lower() != 's':
        exit(1)

# Gerar hash
hash_senha = hashlib.sha256(senha.encode()).hexdigest()

print("\n" + "=" * 50)
print("✅ HASH GERADO COM SUCESSO!")
print("=" * 50)
print()
print("Sua senha:", senha)
print()
print("Hash SHA256:")
print(hash_senha)
print()
print("=" * 50)
print("📝 PRÓXIMOS PASSOS:")
print("=" * 50)
print()
print("1. Copie o hash acima")
print("2. Abra o arquivo: app.py")
print("3. Procure pela linha com 'senha_hash ='")
print("4. Substitua o valor entre aspas pelo hash copiado")
print("5. Salve o arquivo e faça commit")
print()
print("Exemplo:")
print('senha_hash = "' + hash_senha + '"')
print()
