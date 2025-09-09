import os
from flask_dance.contrib.github import make_github_blueprint

# Create GitHub OAuth blueprint
github_bp = make_github_blueprint(
    client_id=os.environ.get('GITHUB_CLIENT_ID'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET'),
    scope="user:email,read:user",  # Request email access
    redirect_to='auth.github_login'  # Redirect to our handler
)
