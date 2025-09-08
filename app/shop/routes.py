from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app.shop import bp
from app.models import User, Book, Cart, Wishlist, GenreEnum
from app import db
from sqlalchemy import and_

def login_required(f):
    """Simple login check decorator"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/cart')
@login_required
def view_cart():
    """Display user's shopping cart"""
    user_id = session['user_id']
    cart_items = db.session.query(Cart, Book).join(Book).filter(Cart.user_id == user_id).all()
    
    total = sum(item.quantity * book.price for item, book in cart_items)
    
    return render_template('shop/cart.html', cart_items=cart_items, total=total)

@bp.route('/add-to-cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    """Add book to cart with AJAX"""
    user_id = session['user_id']
    quantity = int(request.json.get('quantity', 1))
    
    # Get book and check stock
    book = Book.query.get_or_404(book_id)
    if book.stock < quantity:
        return jsonify({
            'success': False, 
            'message': f'Only {book.stock} items available in stock'
        }), 400
    
    # Check if item already exists in cart
    cart_item = Cart.query.filter_by(user_id=user_id, book_id=book_id).first()
    
    if cart_item:
        # Update existing cart item
        new_quantity = cart_item.quantity + quantity
        if new_quantity > book.stock:
            return jsonify({
                'success': False,
                'message': f'Cannot add {quantity} more. Only {book.stock - cart_item.quantity} items available'
            }), 400
        cart_item.quantity = new_quantity
    else:
        # Create new cart item
        cart_item = Cart(user_id=user_id, book_id=book_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    
    # Get cart count for UI update
    cart_count = Cart.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        'success': True,
        'message': f'{book.title} added to cart',
        'cart_count': cart_count
    })

@bp.route('/update-cart/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    """Update cart item quantity with AJAX"""
    user_id = session['user_id']
    quantity = int(request.json.get('quantity', 1))
    
    cart_item = Cart.query.filter_by(id=cart_id, user_id=user_id).first_or_404()
    book = Book.query.get(cart_item.book_id)
    
    if quantity <= 0:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Item removed from cart'})
    
    if quantity > book.stock:
        return jsonify({
            'success': False,
            'message': f'Only {book.stock} items available'
        }), 400
    
    cart_item.quantity = quantity
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Cart updated',
        'new_total': quantity * book.price
    })

@bp.route('/cart-count')
@login_required
def cart_count():
    """Get cart item count for navbar"""
    user_id = session['user_id']
    count = Cart.query.filter_by(user_id=user_id).count()
    return jsonify({'count': count})


@bp.route('/remove-from-cart/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    """Remove item from cart with AJAX"""
    user_id = session['user_id']
    cart_item = Cart.query.filter_by(id=cart_id, user_id=user_id).first_or_404()
    
    db.session.delete(cart_item)
    db.session.commit()
    
    # Get updated cart count
    cart_count = Cart.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        'success': True,
        'message': 'Item removed from cart',
        'cart_count': cart_count
    })

@bp.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    """Clear all items from cart"""
    user_id = session['user_id']
    Cart.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Cart cleared'})

@bp.route('/wishlist')
@login_required
def view_wishlist():
    """Display user's wishlist"""
    user_id = session['user_id']
    wishlist_items = db.session.query(Wishlist, Book).join(Book).filter(Wishlist.user_id == user_id).all()
    
    return render_template('shop/wishlist.html', wishlist_items=wishlist_items)

@bp.route('/add-to-wishlist/<int:book_id>', methods=['POST'])
@login_required
def add_to_wishlist(book_id):
    """Add book to wishlist with AJAX"""
    user_id = session['user_id']
    
    # Check if already in wishlist
    existing = Wishlist.query.filter_by(user_id=user_id, book_id=book_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already in wishlist'})
    
    wishlist_item = Wishlist(user_id=user_id, book_id=book_id)
    db.session.add(wishlist_item)
    db.session.commit()
    
    book = Book.query.get(book_id)
    return jsonify({'success': True, 'message': f'{book.title} added to wishlist'})

@bp.route('/remove-from-wishlist/<int:wishlist_id>', methods=['POST'])
@login_required
def remove_from_wishlist(wishlist_id):
    """Remove item from wishlist"""
    user_id = session['user_id']
    wishlist_item = Wishlist.query.filter_by(id=wishlist_id, user_id=user_id).first_or_404()
    
    db.session.delete(wishlist_item)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Removed from wishlist'})

@bp.route('/checkout')
@login_required
def checkout():
    """Display checkout page"""
    user_id = session['user_id']
    cart_items = db.session.query(Cart, Book).join(Book).filter(Cart.user_id == user_id).all()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('shop.view_cart'))
    
    # Calculate total
    subtotal = sum(item.quantity * book.price for item, book in cart_items)
    
    return render_template('shop/checkout.html', cart_items=cart_items, subtotal=subtotal)
