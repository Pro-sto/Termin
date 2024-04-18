from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
from datetime import timedelta
from datetime import date, time
from flask import session
from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/ldkpr/Desktop/Udemy/Termin/site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '312e386651fa02'
app.config['MAIL_PASSWORD'] = '44969fbd2717c8'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    appointments = db.relationship('Appointment', backref='user', lazy='dynamic')
    

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AppointmentModelView(ModelView):
    form_columns = ['user_id', 'appointment_date', 'appointment_time']  

admin = Admin(app, name='MyApp', template_mode='bootstrap3')
admin.add_view(ModelView(User, db.session))
admin.add_view(AppointmentModelView(Appointment, db.session))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/termin', methods=['GET', 'POST'])
def termin():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        date_str = request.form['date']
        time_str = request.form['time']

        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        existing_appointment = Appointment.query.filter_by(appointment_date=appointment_date, appointment_time=appointment_time).first()
        if existing_appointment:
            flash('Это время уже занято, выберите другое.', 'error')
            return redirect(url_for('termin'))

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(first_name=first_name, last_name=last_name, email=email)
            db.session.add(user)
        
        appointment = Appointment(appointment_date=appointment_date, appointment_time=appointment_time, user=user)
        db.session.add(appointment)
        try:
            db.session.commit()
            msg = Message('Подтверждение записи на прием', sender='your-email@gmail.com', recipients=[email])
            msg.body = f'Sie sind erfolgreich für einen Termin eingetragen. Am {appointment_date} um {appointment_time}. Vergessen Sie nicht, Ihre Krankenversicherungskarte mitzubringen.'
            mail.send(msg)
            flash('Sie sind erfolgreich für einen Termin eingetragen.', 'success')
            return redirect(url_for('index'))
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error(f'Ошибка при регистрации: {str(e)}')
            flash('Ошибка при регистрации. Пожалуйста, попробуйте снова.', 'error')
            return redirect(url_for('termin'))
    else:
        # Добавленный return для гарантирования ответа
        return render_template('termin.html')

    # Добавлен return на случай, если ни одно из условий выше не выполнится
    return redirect(url_for('index'))





@app.route('/get_available_times', methods=['POST'])
def get_available_times():
    date_str = request.json['date']  # Изменено для принятия данных в формате JSON
    chosen_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Получаем все записи на эту дату
    appointments = Appointment.query.filter_by(appointment_date=chosen_date).all()
    booked_times = [appointment.appointment_time.strftime('%H:%M') for appointment in appointments]

    # Генерируем полный список временных слотов на этот день
    start_time = datetime.combine(chosen_date, datetime.strptime('08:00', '%H:%M').time())
    end_time = datetime.combine(chosen_date, datetime.strptime('18:00', '%H:%M').time())
    available_times = []
    current_time = start_time

    while current_time < end_time:
        current_time_str = current_time.strftime('%H:%M')
        if current_time_str not in booked_times:
            available_times.append(current_time_str)
        current_time += timedelta(minutes=20)  # Используем timedelta для увеличения текущего времени

    return jsonify(available_times)


    return render_template('termin.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=8888)


