# 📚 BooksCart - AI-Powered Ecommerce Platform

A full-stack ecommerce application built with Flask, featuring an intelligent AI chatbot, secure payment processing, and comprehensive admin management system.

## 🌟 Live Demo

**🔗 [Visit BooksCart](https://booksflask-production.up.railway.app/)**

- **Customer Experience**: Browse books, add to cart, secure checkout
- **Admin Panel**: Login with GitHub OAuth to access admin features
- **AI Chatbot**: Ask "Taylor" about orders, books, or get assistance

## 🚀 Features

### 🛒 **Customer Features**
- **Book Catalog**: Browse and search books by title, author, or genre
- **Smart Search**: PostgreSQL-powered search with enum compatibility
- **Shopping Cart**: Real-time cart updates and persistent sessions
- **Secure Checkout**: Stripe-powered payment processing
- **Order Tracking**: View order history and status
- **AI Assistant**: Chat with Taylor for personalized help
- **OAuth Login**: GitHub authentication integration

### 👨‍💼 **Admin Features**
- **Inventory Management**: Add, edit, and manage book catalog
- **Order Management**: View and track all customer orders
- **Sales Analytics**: Revenue tracking and order statistics
- **Advanced Chatbot**: Admin-level chatbot capabilities
- **Customer Support**: Access customer order information via AI

### 🤖 **AI Chatbot (Taylor)**
- **Context-Aware Responses**: Understands user queries and provides relevant information
- **Role-Based Access**: Different capabilities for customers vs. admins
- **Order Assistance**: Help with order inquiries and status updates
- **Password Reset**: Assists non-logged users with account recovery
- **Smart Filtering**: Only responds to bookstore-related queries

## 🛠️ Tech Stack

### **Backend**
- **Flask** - Web framework
- **PostgreSQL** - Production database
- **SQLAlchemy** - ORM and database migrations
- **Flask-Login** - User session management
- **Flask-WTF** - Form handling and CSRF protection

### **AI & APIs**
- **OpenAI API** - GPT-powered chatbot
- **LangChain** - AI conversation management
- **Stripe API** - Payment processing and webhooks

### **Authentication & Security**
- **GitHub OAuth** - Social authentication
- **JWT** - Token-based auth
- **Werkzeug** - Password hashing
- **CSRF Protection** - Form security

### **Frontend**
- **Jinja2** - Template engine
- **Bootstrap 5** - Responsive UI framework
- **JavaScript** - Dynamic interactions
- **AJAX** - Real-time cart updates

### **Deployment & Services**
- **Railway** - Cloud hosting platform
- **Gunicorn** - WSGI server
- **Brevo** - Email service integration

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL
- Stripe Account (for payments)
- OpenAI API Key
- GitHub OAuth App
- Brevo Account (for emails)

