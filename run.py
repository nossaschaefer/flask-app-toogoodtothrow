from flask_migrate import Migrate
from flaskblog import app, db
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('API_KEY')


migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, port=5001)


