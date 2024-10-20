from flask import Flask, request, jsonify
import couchdb
from couchdb.http import ResourceNotFound, ResourceConflict, PreconditionFailed
from flask_cors import CORS
from datetime import datetime
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
CORS(app)

# Verbindung zu CouchDB herstellen
couch = couchdb.Server('http://localhost:5984/')
couch.resource.credentials = ('dsadm', 'Leptop12')

# Datenbanken erstellen oder öffnen
try:
    tickets_db = couch.create('tickets')
except PreconditionFailed:
    tickets_db = couch['tickets']

try:
    accounts_db = couch.create('accounts')
except PreconditionFailed:
    accounts_db = couch['accounts']


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    if request.content_type == 'application/json':
        ticket_data = request.json
    else:
        ticket_data = request.form.to_dict()

    new_id = str(datetime.now().timestamp())
    ticket_data['_id'] = new_id
    ticket_data['erstellungsdatum'] = datetime.now().isoformat()
    ticket_data['titel'] = ticket_data.get('titel', '')
    ticket_data['status'] = 'offen'
    ticket_data['schlussdatum'] = None

    # Bilder verarbeiten und als Base64-kodierte Strings speichern
    encoded_images = []
    if 'images' in request.files:
        images = request.files.getlist('images')
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                # Lesen Sie die Bilddaten
                image_data = image.read()
                # Kodieren Sie die Bilddaten in Base64
                encoded_image = base64.b64encode(image_data).decode('utf-8')
                # Speichern Sie die kodierten Bilder in einer Liste
                encoded_images.append({
                    'filename': filename,
                    'data': encoded_image
                })
    elif 'image' in request.files:
        # Einzelnes Bild verarbeiten
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_data = image.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            encoded_images.append({
                'filename': filename,
                'data': encoded_image
            })

    if encoded_images:
        ticket_data['images'] = encoded_images

    # Speichern Sie das Dokument
    tickets_db.save(ticket_data)

    return jsonify({'message': 'Ticket erstellt', 'ticket_id': new_id}), 201


@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    status = request.args.get('status')
    tickets = []

    for doc_id in tickets_db:
        ticket_data = tickets_db.get(doc_id)
        if status is None or ticket_data.get('status') == status:
            tickets.append(ticket_data)

    return jsonify(tickets)


@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
def update_ticket_status(ticket_id):
    try:
        ticket_data = tickets_db[ticket_id]
    except couchdb.ResourceNotFound:
        return jsonify({'message': 'Ticket nicht gefunden'}), 404

    # Den Status und das Schließungsdatum aktualisieren
    new_status = request.json.get('status')
    schlussdatum = request.json.get('schlussdatum')

    if new_status:
        ticket_data['status'] = new_status
        ticket_data['schlussdatum'] = schlussdatum
        tickets_db.save(ticket_data)

    return jsonify({'message': 'Ticketstatus aktualisiert', 'ticket_id': ticket_id}), 200


@app.route('/api/tickets/<ticket_id>/comments', methods=['POST'])
def add_comment(ticket_id):
    try:
        ticket_data = tickets_db[ticket_id]
    except couchdb.ResourceNotFound:
        return jsonify({'message': 'Ticket nicht gefunden'}), 404

    # Kommentar-Daten aus der Anfrage laden
    comment_data = request.json
    kommentare = ticket_data.get('kommentare', [])
    comment_id = str(len(kommentare) + 1)

    # Neuer Kommentar hinzufügen
    new_comment = {
        'kommentar_id': comment_id,
        'inhalt': comment_data.get('inhalt'),
        'zeitstempel': datetime.now().isoformat(),
        'autor': 'admin'  # Passen Sie dies bei Bedarf an
    }

    kommentare.append(new_comment)
    ticket_data['kommentare'] = kommentare
    tickets_db.save(ticket_data)

    return jsonify({'message': 'Kommentar hinzugefügt', 'comment': new_comment}), 201


@app.route('/accounts', methods=['POST'])
def register_account():
    account_data = request.get_json()
    if not account_data:
        return jsonify({'error': 'Keine Daten empfangen'}), 400

    name = account_data.get('name')
    if not name:
        return jsonify({'error': 'Name ist erforderlich'}), 400

    # Überprüfen, ob der Account bereits existiert
    existing_accounts = [doc for doc in accounts_db if accounts_db[doc].get('name') == name]

    if existing_accounts:
        return jsonify({'error': 'Ein Account mit diesem Namen existiert bereits.'}), 400

    # Account-Daten speichern
    account_data['_id'] = str(datetime.now().timestamp())
    try:
        accounts_db.save(account_data)
    except ResourceConflict:
        return jsonify({'error': 'Ein Account mit dieser ID existiert bereits.'}), 400
    except Exception as e:
        print("Fehler beim Speichern des Accounts:", e)
        return jsonify({'error': f'Fehler beim Speichern des Accounts: {str(e)}'}), 500

    return jsonify({'message': 'Account erfolgreich registriert'}), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')

    if not name or not email:
        return jsonify({'success': False, 'message': 'Name und E-Mail sind erforderlich.'}), 400

    # Account suchen
    for account_id in accounts_db:
        account_data = accounts_db[account_id]
        if account_data.get('name') == name and account_data.get('email') == email:
            # Erfolgreiche Anmeldung
            return jsonify({
                'success': True,
                'message': 'Anmeldung erfolgreich.',
                'name': account_data['name'],
                'abteilung': account_data.get('abteilung'),
                'email': account_data['email'],
                'role': account_data.get('role')  # Stellen Sie sicher, dass die Rolle enthalten ist
            }), 200

    # Wenn kein Benutzer gefunden wurde
    return jsonify({'success': False, 'message': 'Benutzer nicht gefunden oder E-Mail stimmt nicht überein.'}), 404



if __name__ == '__main__':
    app.run(debug=True)
