import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
import csv
from datetime import datetime
from io import StringIO
import matplotlib.pyplot as plt
import io
import base64


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///helpdesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo do banco de dados para os chamados
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    attendant = db.Column(db.String(100), nullable=False)
    project = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.String(100), nullable=False)  # Campo para armazenar o tipo de problema
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_open = db.Column(db.String(20), default='Aberto')  # 'Aberto', 'Fechado', 'Ignorado'
    priority = db.Column(db.String(20), nullable=False)




# Função para carregar as cidades do XML com base no projeto
def carregar_cidades(projeto):
    tree = ET.parse('projetos.xml')
    root = tree.getroot()
    
    # Busca o projeto específico
    for proj in root.findall('projeto'):
        if proj.get('nome').lower() == projeto.lower():
            cidades = [{"sigla": cidade.get("sigla"), "nome": cidade.text} for cidade in proj.findall('cidade')]
            return cidades
    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_cidades', methods=['GET'])
def get_cidades():
    projeto = request.args.get('projeto')
    cidades = carregar_cidades(projeto)
    return jsonify(cidades)

@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    project = request.form['project']
    city = request.form['city']
    attendant = request.form['attendant']
    description = request.form['description']
    problem = request.form['problem']  # Captura o tipo de problema
    priority = request.form['priority']
    is_open = request.form['is_open']  # Campo para determinar se o chamado está aberto ou fechado

    new_ticket = Ticket(project=project, city=city, attendant=attendant, 
                         description=description, problem=problem, priority=priority, 
                         is_open=is_open)

    db.session.add(new_ticket)
    db.session.commit()
    flash("Chamado criado com sucesso!", 'success')

    return redirect(url_for('index'))


@app.route('/view_tickets', methods=['GET'])
def view_tickets():
    # Lista de atendentes e projetos (adicionei essas listas para os filtros)
    attendants = ['Marx', 'Rodrigo', 'Rodrigo Budzinsky', 'Silvio']
    projects = ['Streaming', 'PayTV', 'Globo', 'Rádios']
    
    filters = {}
    if 'attendant' in request.args and request.args.get('attendant'):
        filters['attendant'] = request.args.get('attendant')
    if 'project' in request.args and request.args.get('project'):
        filters['project'] = request.args.get('project')
    if 'priority' in request.args and request.args.get('priority'):
        filters['priority'] = request.args.get('priority')
    if 'problem' in request.args and request.args.get('problem'):
        filters['problem'] = request.args.get('problem')
   
    # Ajuste no filtro de status
    if 'is_open' in request.args and request.args.get('is_open'):
        status_filter = request.args.get('is_open')
        if status_filter == 'True':  # Quando "Aberto" for selecionado
            filters['is_open'] = 'Aberto'
        elif status_filter == 'False':  # Quando "Fechado" for selecionado
            filters['is_open'] = 'Fechado'

    # Consulta os tickets filtrando por atendente, projeto, prioridade e status
    tickets = Ticket.query.filter_by(**filters).order_by(
        Ticket.is_open == 'Aberto',  # Coloca 'Aberto' no topo
        Ticket.priority.desc()  # Depois, pela prioridade
    ).all()
    for ticket in tickets:
        ticket.created_at = ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')  # Formatação da data

    return render_template('view.html', tickets=tickets, attendants=attendants, projects=projects)



@app.route('/edit_ticket/<int:id>', methods=['GET', 'POST'])
def edit_ticket(id):
    ticket = Ticket.query.get_or_404(id)

    if request.method == 'POST':
        ticket.description = request.form['description']
        ticket.attendant = request.form['attendant']
        ticket.is_open = request.form['status']  # Now includes 'Ignorar'
        db.session.commit()
        flash("Chamado atualizado com sucesso!", 'success')
        return redirect(url_for('view_tickets'))

    attendants = ['Marx', 'Rodrigo', 'Rodrigo Budzinsky', 'Silvio']
    projects = ['Streaming', 'PayTV', 'Globo', 'Rádios']
    return render_template('edit_ticket.html', ticket=ticket, attendants=attendants, projects=projects)

@app.route('/generate_report', methods=['GET'])
def generate_report():
    tickets = Ticket.query.all()

    # Cria um arquivo CSV em memória
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Descrição', 'Atendente', 'Projeto', 'Cidade', 'Prioridade', 'Status', 'Data de Criação', 'Data de Fechamento'])

    # Adiciona os dados dos chamados no CSV
    for ticket in tickets:
        writer.writerow([ticket.id, ticket.description, ticket.attendant, ticket.project,
                         ticket.city, ticket.priority, ticket.is_open, ticket.created_at, 'N/A' if ticket.is_open == 'Aberto' else ticket.created_at])

    # Volta para o início do arquivo CSV
    output.seek(0)

    # Envia o arquivo CSV para download
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=relatorio_chamados.csv"})

@app.route('/attendant_report', methods=['GET'])
def attendant_report():
    # Contar os chamados por atendente
    attendants_count = db.session.query(Ticket.attendant, db.func.count(Ticket.id)).group_by(Ticket.attendant).all()

    # Separar os dados para o gráfico
    attendants = [attendant for attendant, _ in attendants_count]
    counts = [count for _, count in attendants_count]

    # Gerar o gráfico
    fig, ax = plt.subplots()
    ax.bar(attendants, counts, color='orange')

    ax.set_xlabel('Atendente')
    ax.set_ylabel('Quantidade de Chamados')
    ax.set_title('Chamados por Atendente')

    # Salvar o gráfico em um objeto de imagem em memória
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)

    # Codificar a imagem em base64 para renderização na página
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template('attendant_report.html', plot_url=plot_url)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
    app.run(debug=True)
