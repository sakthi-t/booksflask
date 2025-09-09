from flask import Blueprint

bp = Blueprint('chatbot', __name__)

from app.chatbot import routes
