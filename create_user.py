import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"

def create_user():
    print("--- CRIAR NOVO USUÁRIO ---")
    username = input("Digite o nome de usuário: ")
    password = input("Digite a senha: ")
    
    confirm = input(f"Confirmar criação de '{username}'? (S/N): ")
    if confirm.lower() != 's':
        print("Cancelado.")
        return

    # Gera o Hash da senha (nunca salve senha pura!)
    hashed_pw = generate_password_hash(password)

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Insere no banco
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()
        print(f"\n✅ Sucesso! Usuário '{username}' criado.")
    except sqlite3.IntegrityError:
        print(f"\n❌ Erro: O usuário '{username}' já existe.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    create_user()