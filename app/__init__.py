from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect
from flask_apscheduler import APScheduler
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
csrf = CSRFProtect()
scheduler = APScheduler()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    csrf.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    
    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import bp as admin_bp  # NEW
    app.register_blueprint(admin_bp, url_prefix='/admin')  # NEW

    from app.shop import bp as shop_bp
    app.register_blueprint(shop_bp, url_prefix='/shop')
    
    from app.payment import bp as payment_bp
    app.register_blueprint(payment_bp, url_prefix='/payment')

    from app.chatbot import bp as chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')

    # NEW: Register GitHub OAuth Blueprint
    from app.oauth import github_bp
    app.register_blueprint(github_bp, url_prefix='/login')
    
    
    return app

# Import models after db is created to avoid circular imports
from app import models
