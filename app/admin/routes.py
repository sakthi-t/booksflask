from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from functools import wraps
from app.admin import bp
from app.models import User, Book, Order, Payment, GenreEnum, OrderItem
from app import db, scheduler
from app.config import Config
from sqlalchemy import func

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in via session
        if 'user_id' not in session:
            flash('Please login to access admin area', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user has admin role
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('main.index'))
        
        # Check if user email matches admin email
        if user.email != Config.ADMIN_EMAIL:
            flash('Unauthorized admin access', 'danger')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with overview"""
    # Get statistics
    total_books = Book.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.status.in_(['completed', 'delivered'])).scalar() or 0
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(5).all()
    
    stats = {
        'total_books': total_books,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_books': recent_books
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@bp.route('/books')
@admin_required
def manage_books():
    """Manage books with pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Book.query
    
    if search:
        query = query.filter(
            db.or_(
                Book.title.contains(search),
                Book.author.contains(search)
            )
        )
    
    books = query.order_by(Book.created_at.desc()).paginate(
        page=page, per_page=8, error_out=False  # 8 books per page
    )
    
    return render_template('admin/manage_books.html', books=books, search=search)

@bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    """Add new book"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title')
            author = request.form.get('author')
            price = float(request.form.get('price'))
            description = request.form.get('description')
            image_url = request.form.get('image_url')
            stock = int(request.form.get('stock', 0))
            genre_value = request.form.get('genre')
            
            # Convert genre string to enum
            genre = GenreEnum(genre_value)
            
            # Create new book
            book = Book(
                title=title,
                author=author,
                price=price,
                description=description,
                image_url=image_url,
                stock=stock,
                genre=genre
            )
            
            db.session.add(book)
            db.session.commit()
            
            flash(f'Book "{title}" added successfully!', 'success')
            return redirect(url_for('admin.manage_books'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'danger')
    
    return render_template('admin/add_book.html', genres=GenreEnum)

@bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    """Edit existing book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            book.title = request.form.get('title')
            book.author = request.form.get('author')
            book.price = float(request.form.get('price'))
            book.description = request.form.get('description')
            book.image_url = request.form.get('image_url')
            book.stock = int(request.form.get('stock', 0))
            
            # Update genre if provided
            genre_value = request.form.get('genre')
            if genre_value:
                book.genre = GenreEnum(genre_value)
            
            db.session.commit()
            
            flash(f'Book "{book.title}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_books'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {str(e)}', 'danger')
    
    return render_template('admin/edit_book.html', book=book, genres=GenreEnum)


@bp.route('/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    """Delete book"""
    book = Book.query.get_or_404(book_id)

    from app.models import OrderItem
    has_orders = OrderItem.query.filter_by(book_id=book_id).first()
    
    if has_orders:
        flash(f'Cannot delete "{book.title}" - it has been ordered by customers. You can edit it instead.', 'warning')
        return redirect(url_for('admin.manage_books'))
    
    try:
        title = book.title
        db.session.delete(book)
        db.session.commit()
        flash(f'Book "{title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_books'))

@bp.route('/orders')
@admin_required
def view_orders():
    """View all orders"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@bp.route('/orders/<int:order_id>/details')
@admin_required
def order_details(order_id):
    """View detailed order information including payment"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)


@bp.route('/orders/update-status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Update order status"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    valid_statuses = ['pending', 'in_progress', 'delivered', 'cancelled', 'delayed', 'refunded']

    
    if new_status in valid_statuses:
        old_status = order.status  # NOW defined properly
    
    if new_status in ['pending', 'in_progress', 'delivered', 'cancelled', 'delayed', 'refunded']:
           # Handle stock restoration for cancelled/refunded orders
        if new_status in ['cancelled', 'refunded'] and old_status not in ['cancelled', 'refunded']:
            for order_item in order.items:
                book = Book.query.get(order_item.book_id)
                if book:
                    book.stock += order_item.quantity
                    print(f"Restored {order_item.quantity} units of {book.title} (new stock: {book.stock})")
        
        # Handle stock reduction if moving from cancelled/refunded back to active
        elif old_status in ['cancelled', 'refunded'] and new_status not in ['cancelled', 'refunded']:
            for order_item in order.items:
                book = Book.query.get(order_item.book_id)
                if book:
                    if book.stock >= order_item.quantity:
                        book.stock -= order_item.quantity
                        print(f"Reduced {order_item.quantity} units of {book.title} (new stock: {book.stock})")
                    else:
                        flash(f'Insufficient stock for {book.title}. Current stock: {book.stock}, required: {order_item.quantity}', 'danger')
                        return redirect(url_for('admin.view_orders'))




        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.id} status updated to {new_status}', 'success')
    else:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('admin.view_orders'))

@bp.route('/orders/override-status/<int:order_id>', methods=['POST'])
@admin_required
def override_order_status(order_id):
    """Admin override of order status"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    valid_statuses = ['pending', 'in_progress', 'delivered', 'cancelled', 'delayed', 'refunded']
    
    if new_status in valid_statuses:
        old_status = order.status
        order.status = new_status
        
        # If admin refunds, restore stock
        if new_status == 'refunded' and old_status != 'refunded':
            for order_item in order.items:
                book = Book.query.get(order_item.book_id)
                book.stock += order_item.quantity
        
        db.session.commit()
        
        # Cancel any scheduled jobs for this order
        try:
            from app import scheduler
            scheduler.remove_job(f'deliver_order_{order_id}')
        except:
            pass
        try:
            scheduler.remove_job(f'delay_order_{order_id}')
        except:
            pass
        
        flash(f'Order #{order_id} status updated to {new_status}', 'success')
    else:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('admin.view_orders'))

