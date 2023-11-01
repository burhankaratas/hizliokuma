import re
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request,g
from wtforms import Form,StringField,TextAreaField,PasswordField,validators, SubmitField
from passlib.hash import sha256_crypt
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError
from functools import wraps
from datetime import datetime
import hashlib
import smtplib

app = Flask(__name__)


db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///C:/Users/burha/OneDrive/Desktop/Hızlı Okuma Programı/hizliokuma.db"
db.init_app(app)

app.config['PERMANENT_SESSION_LIFETIME'] = 565656456
app.secret_key = "aepfjaepofjpoaefj"

def is_valid_email(email):
    try:
        # E-posta adresini doğrula
        v = validate_email(email)
        return True

    except EmailNotValidError as e:
        # E-posta geçerli değil
        print(f"E-posta doğrulama hatası: {str(e)}")
        return False
    

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session and session["logged_in"]:
            # Kullanıcı oturumu açık, işlemi gerçekleştir
            return f(*args, **kwargs)
        else:
            # Kullanıcı oturumu açık değil, hata mesajı göster ve giriş sayfasına yönlendir
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "danger")
            return redirect(url_for("loginPage"))
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in"):
            user = User.query.filter_by(username=session["username"]).first()
            if user.is_admin:
                return f(*args, **kwargs)
            else:
                flash("Bu sayfaya erişmek için yönetici olmalısınız.", "danger")
                return redirect(url_for("indexPage"))
        else:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "danger")
            return redirect(url_for("loginPage"))
    return decorated_function
    

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in"):
            user = User.query.filter_by(username=session["username"]).first()
            if user.is_teacher:
                return f(*args, **kwargs)
            else:
                flash("Bu sayfaya erişmek için öğretmen olmalısınız.", "danger")
                return redirect(url_for("indexPage"))
        else:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "danger")
            return redirect(url_for("loginPage"))
    return decorated_function


MAX_STUDENTS_PER_TEACHER = 4

def find_empty_student_slot(teacher):
    for i in range(1, MAX_STUDENTS_PER_TEACHER + 1):
        field_name = f"teacherstudent{i}"
        if not getattr(teacher, field_name):
            return field_name
    return None  # Tüm öğrenci alanları doluysa None döndür


    
@app.route("/")
def indexPage():
    admin = False
    if session.get("logged_in"):
        user = User.query.filter_by(username=session["username"]).first()  # Sonucu alın
        if user.is_admin:
            admin = True
            return render_template("admin.html", admin = admin)
        elif user.is_teacher:
            return render_template("teacher.html")
        else:
            return render_template("app.html")
    else:
        return render_template("index.html")



@app.route("/hakkimizda")
def aboutPage():
    return render_template("hakkimizda.html")



@app.route("/register", methods=["GET", "POST"])
def registerPage():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        email = form.email.data
        phone = form.phone.data
        password = form.password.data
        password_again = form.passwordAgain.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Bu kullanıcı adı zaten kullanılıyor. Lütfen farklı bir kullanıcı adı seçin.", "danger")
            return render_template("register.html", form=form)

        if password != password_again:
            flash("Şifreler eşleşmiyor. Lütfen aynı şifreyi girin.", "danger")
            return render_template("register.html", form=form)

        if not is_valid_email(email):
            flash("Geçerli bir e-posta adresi girin.", "danger")
            return render_template("register.html", form=form)

        hashed_password = sha256_crypt.hash(password)

        new_user = User(username=username, email=email, phone=phone, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Kayıt başarıyla tamamlandı.", "success")
        return redirect(url_for("loginPage"))

    return render_template("register.html", form=form)



@app.route("/login", methods=["GET", "POST"])
def loginPage():
    form = LoginForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        password_candidate = form.password.data

        user = User.query.filter_by(username=username).first()
        if user:
            # Kullanıcı adı bulundu, şifre doğrulaması yapın
            if sha256_crypt.verify(password_candidate, user.password):
                # Şifre doğrulandı, oturum aç
                session["logged_in"] = True
                session["username"] = username

                session.permanent = True

                flash("Başarıyla giriş yaptınız.", "success")
                return redirect(url_for("indexPage"))
            else:
                flash("Geçersiz şifre.", "danger")
                return render_template("login.html", form=form)
        else:
            flash("Kullanıcı adı bulunamadı.", "danger")
            return render_template("login.html", form=form)

    return render_template("login.html", form=form)



@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yapıldı. İçeriklere erişmek için giriş yapın", "success")
    return redirect(url_for("loginPage"))


@app.route("/haberler")
def haberlerPage():
    if session.get("logged_in"):
        user = User.query.filter_by(username=session["username"]).first()  # Sonucu alın


        if user.is_admin:
            admin = True
            haberler = Haberler.query.all()

            return render_template("haberler.html", admin = admin, haberler = haberler)
        
        else:
            haberler = Haberler.query.all()

            return render_template('haberler.html', haberler = haberler)
        
    haberler = Haberler.query.all()

    return render_template('haberler.html', haberler = haberler)


@app.route("/sss")
def sssPage():
    return render_template("sss.html")




@app.route("/haberler/<int:id>")
def haberPage(id):
    haber = Haberler.query.get(id)
    
    if haber is None:
        flash("Belirtilen haber bulunamadı.", "danger")
        return redirect(url_for("haberlerPage"))
    
    return render_template("haber.html", haber=haber)

@app.route("/haber-ekle", methods = ["GET", "POST"])
@admin_required
def haberEklePage():

    if request.method == "GET":
        return render_template("haberekle.html")
    
    elif request.method == "POST":
        baslik = request.form.get("baslik")
        icerik = request.form.get("icerik")

        # Yeni bir Haberler nesnesi oluşturun ve verileri atayın
        yeni_haber = Haberler(baslik=baslik, icerik=icerik, date=datetime.utcnow())

        try:
            # Yeni haber nesnesini veritabanına ekleyin
            db.session.add(yeni_haber)
            db.session.commit()

            flash("Haber başarıyla eklendi.", "success")
            return redirect(url_for("haberEklePage"))
        except Exception as e:
            # Hata durumunda geri al ve hatayı görüntüle
            db.session.rollback()
            flash("Haber eklenirken bir hata oluştu.", "danger")
    else:
        return render_template("haberekle.html")
    
@app.route("/haber-sil/<int:id>")
@admin_required
def haberSil(id):
    silinecek_haber = Haberler.query.get(id)

    if silinecek_haber is None:
        flash("Belirtilen haber bulunamadı.", "danger")
        return redirect(url_for("haberlerPage"))

    try:
        db.session.delete(silinecek_haber)
        db.session.commit()
        flash("Haber başarıyla silindi.", "success")
    except Exception as e:
        flash("Haber silinirken bir hata oluştu: " + str(e), "danger")
        db.session.rollback()

    return redirect(url_for("haberlerPage"))


@app.route("/ogretmen-hesap-ekle")
@admin_required
def ogretmenHesapEklePage():
    # Tüm kullanıcıları çekmek için bir sorgu yapın
    users = User.query.all()

    return render_template("ogretmenhesapekle.html", users=users)


@app.route("/set-teacher/<username>", methods=["POST"])
@admin_required  # Sadece admin yetkisine sahip kullanıcılar tarafından erişilebilir yapabilirsiniz
def set_teacher(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.is_teacher = True
        db.session.commit()
        return ("", 200)  # Başarılı yanıt
    else:
        return ("", 404)  # Kullanıcı bulunamadı

@app.route("/remove-teacher/<username>", methods=["POST"])
@admin_required  # Sadece admin yetkisine sahip kullanıcılar tarafından erişilebilir yapabilirsiniz
def remove_teacher(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.is_teacher = False
        db.session.commit()
        return ("", 200)  # Başarılı yanıt
    else:
        return ("", 404)  # Kullanıcı bulunamadı

# ...

@app.route("/ogrenci-ekle", methods=["GET", "POST"])
@teacher_required
def ogrenciEklePage():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        email = form.email.data
        phone = form.phone.data
        password = form.password.data
        password_again = form.passwordAgain.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Bu kullanıcı adı zaten kullanılıyor. Lütfen farklı bir kullanıcı adı seçin.", "danger")
            return render_template("ogrenciekle.html", form=form)

        if password != password_again:
            flash("Şifreler eşleşmiyor. Lütfen aynı şifreyi girin.", "danger")
            return render_template("ogrenciekle.html", form=form)

        hashed_password = sha256_crypt.hash(password)

        # Öğretmenin öğrenci alanlarını kontrol edin ve boş olan bir yeri bulun
        teacher = User.query.filter_by(username=session["username"]).first()
        empty_slot = find_empty_student_slot(teacher)
        if empty_slot:
            setattr(teacher, empty_slot, username)  # Öğrenci alanını doldurun
            new_user = User(username=username, email=email, phone=phone, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Öğrenci başarıyla eklediniz.", "success")
        else:
            flash("Öğrenci eklemek için sınıra ulaştınız.", "danger")

        return redirect(url_for("indexPage"))

    return render_template("ogrenciekle.html", form=form)



@app.route("/ogrencilerim")
@teacher_required
def ogrencilerim():
    # Öğretmenin öğrencilerini çekin
    teacher = User.query.filter_by(username=session["username"]).first()
    student_usernames = [getattr(teacher, f"teacherstudent{i}") for i in range(1, MAX_STUDENTS_PER_TEACHER + 1) if getattr(teacher, f"teacherstudent{i}")]
    
    # Öğrenci kullanıcı adlarına göre öğrenci nesnelerini çekin
    students = User.query.filter(User.username.in_(student_usernames)).all()
    
    return render_template("ogrencilerim.html", students=students)


@app.route("/ogrenci-sil/<username>", methods=["POST"])
@teacher_required
def ogrenciSil(username):
    teacher = User.query.filter_by(username=session["username"]).first()

    # Öğrencinin veritabanındaki alanını temizleyin
    for i in range(1, MAX_STUDENTS_PER_TEACHER + 1):
        student_slot = getattr(teacher, f"teacherstudent{i}")
        if student_slot == username:
            setattr(teacher, f"teacherstudent{i}", None)
            db.session.commit()
            flash(f"{username} adlı öğrenciyi başarıyla sildiniz.", "success")
            return redirect(url_for("ogrencilerim"))

    flash("Öğrenci bulunamadı veya silinemedi.", "danger")
    return redirect(url_for("ogrencilerim"))



@app.route("/dersler")
@login_required
def derslerPage():
    return render_template("dersler.html")

@app.route("/hesap")
@login_required
def hesapPage():
    return render_template("hesap.html")

@app.route("/kisisel-bilgilerim")
@login_required
def kisiselBilgilerPage():
    return render_template("kisiselbilgiler.html")



class LoginForm(Form):
    username = StringField(validators=[validators.InputRequired()])
    password = PasswordField(validators=[validators.InputRequired()])


class RegisterForm(Form):
    username = StringField(validators=[validators.length(min=5, max=25),validators.InputRequired()])
    email = StringField(validators=[validators.Email(), validators.InputRequired()])
    phone = StringField(validators=[validators.length(min=10, max=10), validators.InputRequired()])
    password = PasswordField(validators=[validators.length(min=8, max=40), validators.InputRequired()])
    passwordAgain = PasswordField(validators=[validators.length(min=8, max=40),  validators.InputRequired()])


class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min=3, max=50)])
    content = TextAreaField("İçerik", validators=[validators.length(min=10)])



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String)
    phone = db.Column(db.String)
    password = db.Column(db.String)
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)
    teacherstudent1 = db.Column(db.String)
    teacherstudent2 = db.Column(db.String)
    teacherstudent3 = db.Column(db.String)
    teacherstudent4 = db.Column(db.String)


class Haberler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String)
    icerik = db.Column(db.String)
    date = db.Column(db.DateTime, default=datetime.utcnow) 

    




# AŞŞAĞISI GÜNLER VE GÜN İÇERİKLERİ İNME ÇIKAMAZSIN :D

@app.route("/daily/1")
def daily1Page():
    return render_template("daily/daily1.html")

@app.route("/daily/2")
def daily2Page():
    return render_template("daily/daily2.html")

@app.route("/daily/3")
def daily3Page():
    return render_template("daily/daily3.html")

@app.route("/daily/4")
def daily4Page():
    return render_template("daily/daily4.html")

@app.route("/daily/5")
def daily5Page():
    return render_template("daily/daily5.html")

@app.route("/daily/6")
def daily6Page():
    return render_template("daily/daily6.html")

@app.route("/daily/7")
def daily7Page():
    return render_template("daily/daily7.html")




if __name__ == "__main__":
    # Veritabanı tablosunu oluştur
    with app.app_context():
        db.create_all()

    app.run(debug=True)