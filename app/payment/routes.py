import stripe
import os
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app.payment import bp
from app.models import User, Book, Cart, Order, OrderItem, Payment, GenreEnum
from app import db, scheduler, csrf
from app.config import Config
from datetime import datetime


# Configure Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

def login_required(f):
    """Simple login check decorator"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session with AJAX"""
    try:
        user_id = session['user_id']
        cart_items = db.session.query(Cart, Book).join(Book).filter(Cart.user_id == user_id).all()
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Validate stock availability
        for cart_item, book in cart_items:
            if book.stock < cart_item.quantity:
                return jsonify({
                    'error': f'Insufficient stock for {book.title}. Only {book.stock} available.'
                }), 400
        
        # Create line items for Stripe
        line_items = []
        for cart_item, book in cart_items:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': book.title,
                        'description': f'by {book.author}',
                    },
                    'unit_amount': int(book.price * 100),  # Convert to cents
                },
                'quantity': cart_item.quantity,
            })
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.host_url + 'payment/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'shop/cart',
            metadata={
                'user_id': user_id
            }
        )
        
        return jsonify({'sessionId': checkout_session.id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/success')
@login_required
def payment_success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Retrieve the session from Stripe
            session_data = stripe.checkout.Session.retrieve(session_id)
            
            if session_data.payment_status == 'paid':
                flash('Payment successful! Your order has been placed.', 'success')
            else:
                flash('Payment verification pending.', 'info')
                
        except Exception as e:
            flash('Error verifying payment. Please contact support.', 'danger')
    
    return redirect(url_for('main.index'))

@csrf.exempt 
@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    print(f"Webhook received - Signature: {sig_header[:20] if sig_header else 'None'}...")
    print(f"Payload length: {len(payload)}")

    webhook_secret = Config.STRIPE_WEBHOOK_SECRET or os.environ.get('STRIPE_WEBHOOK_SECRET')
    print(f"Using webhook secret: {webhook_secret[:10] if webhook_secret else 'None'}...")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
        print(f"Event type: {event['type']}")
    except ValueError as e:
        print(f"Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
        return 'Invalid signature', 400
    
    # Handle checkout session completed
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        print(f"Processing checkout session: {session_data.get('id')}")
        try:
            handle_successful_payment(session_data)
            print("Payment processed successfully")
        except Exception as e:
            print(f"Error in handle_successful_payment: {e}")
            return 'Processing error', 400
    
    return 'Success', 200

def handle_successful_payment(session_data):
    """Process successful payment and create order"""
    try:
        user_id = int(session_data['metadata']['user_id'])
        
        # Get cart items
        cart_items = db.session.query(Cart, Book).join(Book).filter(Cart.user_id == user_id).all()
        
        if not cart_items:
            return
        
        # Calculate total
        total_amount = sum(cart_item.quantity * book.price for cart_item, book in cart_items)
        
        # Create order
        order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status='in_progress'
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items and update stock
        fiction_only = True
        for cart_item, book in cart_items:
            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                book_id=book.id,
                quantity=cart_item.quantity,
                price=book.price
            )
            db.session.add(order_item)
            
            # Update stock
            book.stock -= cart_item.quantity
            
            # Check if order contains non-fiction
            if book.genre != GenreEnum.FICTION:
                fiction_only = False
        
        # Create payment record
        payment = Payment(
            order_id=order.id,
            payment_method='stripe',
            transaction_id=session_data['payment_intent'],
            amount=total_amount,
            status='completed'
        )
        db.session.add(payment)
        
        # Clear cart
        Cart.query.filter_by(user_id=user_id).delete()
        
        db.session.commit()
        
        # Schedule automatic status update
        schedule_order_status_update(order.id, fiction_only)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing payment: {e}")

def schedule_order_status_update(order_id, fiction_only):
    """Schedule order status update using APScheduler"""
    if fiction_only:
        # Fiction books - mark as delivered immediately
        scheduler.add_job(
            func=update_order_status_to_delivered,
            trigger="date",
            run_date=datetime.now(),
            args=[order_id],
            id=f'deliver_order_{order_id}'
        )
    else:
        # Non-fiction books - mark as delayed immediately
        scheduler.add_job(
            func=update_order_status_to_delayed,
            trigger="date",
            run_date=datetime.now(),
            args=[order_id],
            id=f'delay_order_{order_id}'
        )

def update_order_status_to_delivered(order_id):
    """Update order status to delivered"""
    try:
        order = Order.query.get(order_id)
        if order and order.status == 'in_progress':
            order.status = 'delivered'
            db.session.commit()
            print(f"Order {order_id} marked as delivered")
    except Exception as e:
        print(f"Error updating order {order_id} to delivered: {e}")

def update_order_status_to_delayed(order_id):
    """Update order status to delayed"""
    try:
        order = Order.query.get(order_id)
        if order and order.status == 'in_progress':
            order.status = 'delayed'
            db.session.commit()
            print(f"Order {order_id} marked as delayed")
    except Exception as e:
        print(f"Error updating order {order_id} to delayed: {e}")

@bp.route('/order-action/<int:order_id>', methods=['POST'])
@login_required
def handle_order_action(order_id):
    """Handle customer actions on delayed orders"""
    user_id = session['user_id']
    action = request.json.get('action')
    
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    
    if order.status != 'delayed':
        return jsonify({'success': False, 'message': 'Action not allowed for this order'})
    
    if action == 'accept':
        # Customer accepts delayed order - mark as delivered
        order.status = 'delivered'
        db.session.commit()
        
        # Cancel any pending scheduled jobs
        try:
            scheduler.remove_job(f'delay_order_{order_id}')
        except:
            pass
        
        return jsonify({'success': True, 'message': 'Order accepted and marked as delivered'})
    
    elif action == 'decline':
        # Customer declines delayed order - cancel and restore stock
        order.status = 'cancelled'
        
        # Restore stock
        for order_item in order.items:
            book = Book.query.get(order_item.book_id)
            book.stock += order_item.quantity
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order cancelled and stock restored'})
    
    return jsonify({'success': False, 'message': 'Invalid action'})
