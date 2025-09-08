from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app.main import bp
from app.models import Book, User, Order
from app import db

@bp.route('/')
def index():
    # Get recent books (6 latest)
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(6).all()
    return render_template('index.html', recent_books=recent_books)

@bp.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Book.query
    
    if search:
        query = query.filter(
            db.or_(
                Book.title.contains(search),
                Book.author.contains(search),
                Book.genre.contains(search)
            )
        )
    
    books = query.order_by(Book.created_at.desc()).paginate(
        page=page, per_page=8, error_out=False
    )
    
    return render_template('main/books.html', books=books, search=search)

@bp.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('main/book_detail.html', book=book)

@bp.route('/orders')
def user_orders():
    """Display user's order history"""
    if 'user_id' not in session:
        flash('Please login to view orders', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('main/orders.html', orders=orders)
