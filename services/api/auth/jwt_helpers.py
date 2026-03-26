# create_access_token, create_refresh_token, decode_token
import os

JWT_ALGO = os.getenv("ALGO_SECRET")
JWT_SECRET = os.getenv("SECRET_JWT")
JWT_MINS = os.getenv("ACCESS_TOKEN_MINS") 
JWT_DAYS = os.getenv("ACCESS_TOKEN_DAYS")


def create_access_token():
    """ """


def create_refresh_token():
    """ """


def decode_token():
    """ """
