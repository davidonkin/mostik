from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp

class LoginForm(FlaskForm):
    phone = StringField('Телефон', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    phone = StringField('Телефон', validators=[DataRequired(), Length(min=10, max=15), Regexp(r'^[0-9]*$', message="Только цифры")])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')
