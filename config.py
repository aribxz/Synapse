# Config is the office
import os  # Bridge between os and computer system.

class config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key") 