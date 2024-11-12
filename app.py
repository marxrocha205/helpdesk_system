from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'secret_key'

# Configuração de logs
logging.basicConfig(filename='logs/error.log', level=logging.ERROR)

# Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicialização do banco de dados
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT,
            description TEXT,
            attendant TEXT,
            date TEXT,
            priority TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Rota para a página inicial (criação de chamado)
@app.route('/')
def index():
    return render_template('index.html')

# Rota para adicionar um novo chamado
@app.route('/add_ticket', methods=['POST'])
def add_ticket():
    try:
        tag = request.form['tag']
        description = request.form['description']
        attendant = request.form['attendant']
        priority = request.form['priority']
        date = datetime.now().strftime('%d/%m/%Y')
        status = 'Aberto'

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO tickets (tag, description, attendant, date, priority, status) VALUES (?, ?, ?, ?, ?, ?)',
            (tag, description, attendant, date, priority, status)
        )
        conn.commit()
        conn.close()
        flash('Chamado criado com sucesso!')
    except Exception as e:
        logging.error(f"Erro ao criar chamado: {e}")
        flash('Erro ao criar chamado.')
    return redirect(url_for('index'))

# Rota para visualizar os chamados
@app.route('/view_tickets')
def view_tickets():
    try:
        conn = get_db_connection()
        tickets = conn.execute('''
            SELECT * FROM tickets ORDER BY
            CASE priority WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
            CASE status WHEN 'Aberto' THEN 1 ELSE 2 END
        ''').fetchall()
        conn.close()
        return render_template('view_tickets.html', tickets=tickets)
    except Exception as e:
        logging.error(f"Erro ao visualizar chamados: {e}")
        flash('Erro ao carregar os chamados.')
        return redirect(url_for('index'))

# Rota para editar um chamado
@app.route('/edit_ticket/<int:id>', methods=['GET', 'POST'])
def edit_ticket(id):
    conn = get_db_connection()
    ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        try:
            tag = request.form['tag']
            description = request.form['description']
            attendant = request.form['attendant']
            priority = request.form['priority']
            status = request.form['status']

            conn.execute(
                'UPDATE tickets SET tag = ?, description = ?, attendant = ?, priority = ?, status = ? WHERE id = ?',
                (tag, description, attendant, priority, status, id)
            )
            conn.commit()
            flash('Chamado atualizado com sucesso!')
        except Exception as e:
            logging.error(f"Erro ao editar chamado: {e}")
            flash('Erro ao atualizar chamado.')
        finally:
            conn.close()
            return redirect(url_for('view_tickets'))

    return render_template('edit_ticket.html', ticket=ticket)

# Rota para excluir um chamado
@app.route('/delete_ticket/<int:id>')
def delete_ticket(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM tickets WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Chamado excluído com sucesso!')
    except Exception as e:
        logging.error(f"Erro ao excluir chamado: {e}")
        flash('Erro ao excluir chamado.')
    return redirect(url_for('view_tickets'))

if __name__ == '__main__':
    app.run(debug=True)
