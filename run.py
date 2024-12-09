from flask_migrate import Migrate
from flaskblog import app, db
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve the API key from the environment
API_KEY = os.getenv('API_KEY')

# Initialize Google Maps client with the retrieved API key
if API_KEY:
    import googlemaps
    gmaps = googlemaps.Client(key=API_KEY)
else:
    raise ValueError("API Key is missing from environment variables.")



migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, port=5001)


