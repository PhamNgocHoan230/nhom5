from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Product
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----- PHÂN QUYỀN -----
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            flash("Bạn không có quyền truy cập trang quản trị.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ----- TRANG CHỦ -----
@app.route('/')
def index():
    return render_template('index.html')

# ----- DANH SÁCH SẢN PHẨM -----
@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    category = request.args.get('category')  # Lấy category từ query string
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    products = query.paginate(page=page, per_page=per_page)
    return render_template('products.html', products=products, current_category=category)

# ----- CHI TIẾT SẢN PHẨM -----
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

# ----- API TOP 10 SẢN PHẨM -----
@app.route('/top-products')
def top_products():
    top10 = Product.query.order_by(Product.sales.desc()).limit(10).all()
    return jsonify([
        {'name': p.name, 'sales': p.sales}
        for p in top10
    ])

# ===== ĐĂNG NHẬP/ĐĂNG KÝ/ĐĂNG XUẤT KHÁCH HÀNG =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            # Admin thì chuyển vào dashboard, khách thì về trang chủ
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu sai', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, password=generate_password_hash(password), is_admin=False)
        db.session.add(user)
        db.session.commit()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ===== ĐĂNG NHẬP ADMIN =====
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password) and user.is_admin:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Sai thông tin quản trị!', 'danger')
    return render_template('admin/admin_login.html')

# ===== ADMIN DASHBOARD =====
@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

# ===== QUẢN TRỊ NGƯỜI DÙNG =====
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = True if request.form.get('is_admin') else False
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('add_user'))
        user = User(username=username, password=generate_password_hash(password), is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        flash('Đã thêm người dùng mới!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/add_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])
        user.is_admin = True if request.form.get('is_admin') else False
        db.session.commit()
        flash('Đã cập nhật người dùng!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không được xóa admin!', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('Đã xóa người dùng!', 'success')
    return redirect(url_for('admin_users'))

# ===== QUẢN TRỊ SẢN PHẨM =====
@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        sales = int(request.form.get('sales', 0))
        desc = request.form['description']
        category = request.form.get('category', 'sanpham1')
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            # Đảm bảo thư mục upload tồn tại
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = f'/static/uploads/{filename}'
        else:
            flash('Vui lòng chọn đúng định dạng ảnh!', 'danger')
            return redirect(request.url)
        product = Product(
            name=name, price=price, image=image_url,
            sales=sales, description=desc, category=category
        )
        db.session.add(product)
        db.session.commit()
        flash('Đã thêm sản phẩm mới!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.image = request.form['image']
        product.sales = int(request.form.get('sales', 0))
        product.description = request.form['description']
        db.session.commit()
        flash('Đã cập nhật sản phẩm!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm!', 'success')
    return redirect(url_for('admin_products'))
@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy_product(product_id):
    if 'user_id' not in session:
        flash("Bạn cần đăng nhập để mua hàng!", "warning")
        return redirect(url_for('login', next=url_for('buy_product', product_id=product_id)))
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        address = request.form['address']
        # Ở đây bạn có thể lưu thông tin đơn hàng vào DB nếu muốn
        flash("Đặt hàng thành công! Đơn hàng sẽ được giao tới địa chỉ: {}".format(address), "success")
        return redirect(url_for('product_detail', product_id=product_id))
    return render_template('buy_product.html', product=product)
def create_admin():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('123456'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)