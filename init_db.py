import sqlite3

# Conecta ao banco
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Verifica as colunas existentes
cursor.execute("PRAGMA table_info(estudantes);")
colunas = [col[1] for col in cursor.fetchall()]

# Se ainda existe a coluna 'sobrenome', vamos recriar a tabela
if 'sobrenome' in colunas:
    print("⚠️ Campo 'sobrenome' encontrado. Atualizando estrutura...")

    # 1. Renomeia a tabela original
    cursor.execute("ALTER TABLE estudantes RENAME TO estudantes_old;")

    # 2. Cria a nova tabela sem 'sobrenome'
    cursor.execute('''
        CREATE TABLE estudantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            numero_bi TEXT UNIQUE,
            curso TEXT,
            periodo TEXT,
            ano_frequencia TEXT
        );
    ''')

    # 3. Copia os dados sem o campo 'sobrenome'
    cursor.execute('''
        INSERT INTO estudantes (id, nome, data_nascimento, numero_bi, curso, periodo, ano_frequencia)
        SELECT id, nome, data_nascimento, numero_bi, curso, periodo, ano_frequencia
        FROM estudantes_old;
    ''')

    # 4. Exclui a tabela antiga
    cursor.execute("DROP TABLE estudantes_old;")
    print("✅ Estrutura atualizada com sucesso.")
else:
    print("✅ Tabela 'estudantes' já está correta.")

conn.commit()
conn.close()
