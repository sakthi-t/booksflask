from app import create_app, db
from app.models import User, Book, GenreEnum  # ← You were missing GenreEnum import
from sqlalchemy.exc import SQLAlchemyError

app = create_app()

with app.app_context():
    # Create admin user if not exists  
    admin_email = 't.shakthi@gmail.com'  # Your admin email
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(username='admin', email=admin_email, role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("Admin user created")
    else:
        # Update existing user to admin role
        admin.role = 'admin'
        print("Admin role updated")

    # Sample books data as dictionaries for safe upsert
    sample_books = [
        {'title': 'Python Programming', 'author': 'John Doe', 'price': 29.99, 
         'description': 'Learn Python programming from scratch', 'genre': GenreEnum.OTHER, 'stock': 10},
        {'title': 'Web Development', 'author': 'Jane Smith', 'price': 39.99,
         'description': 'Complete guide to web development', 'genre': GenreEnum.OTHER, 'stock': 15},
        {'title': 'Data Science Basics', 'author': 'Bob Johnson', 'price': 49.99,
         'description': 'Introduction to data science', 'genre': GenreEnum.FICTION, 'stock': 8},
        {'title': 'Machine Learning', 'author': 'Alice Brown', 'price': 59.99,
         'description': 'ML concepts and implementations', 'genre': GenreEnum.OTHER, 'stock': 12},
        {'title': 'Flask Web Development', 'author': 'Miguel Grinberg', 'price': 45.99,
         'description': 'Building web applications with Flask', 'genre': GenreEnum.NONFICTION, 'stock': 20},
        {'title': 'JavaScript Guide', 'author': 'David Wilson', 'price': 35.99,
         'description': 'Modern JavaScript development', 'genre': GenreEnum.PHILOSOPHY, 'stock': 18}
    ]

    # Safe upsert: update existing or create new
    for book_data in sample_books:
        existing_book = Book.query.filter_by(title=book_data['title']).first()
        
        if existing_book:
            # Update existing book with all fields including genre
            existing_book.author = book_data['author']
            existing_book.price = book_data['price']
            existing_book.description = book_data['description']
            existing_book.genre = book_data['genre']
            existing_book.stock = book_data['stock']
            print(f"Updated: {existing_book.title}")
        else:
            # Create new book
            new_book = Book(**book_data)
            db.session.add(new_book)
            print(f"Created: {new_book.title}")

    # Commit all changes with error handling
    try:
        db.session.commit()
        print("Sample data created/updated successfully!")
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Failed to create sample data: {e}")
