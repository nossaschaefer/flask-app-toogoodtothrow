from flask_migrate import Migrate
from flaskblog import app, db

migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, port=5001)