from methods import *
from uuid import uuid4


from fastapi import FastAPI, Response, status, Depends, Query, File, UploadFile, HTTPException
from typing import Optional, List, Union
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette.responses import FileResponse

import db_models
from db_connect import engine, SessionLocal
from sqlalchemy.orm import Session
from minio import Minio
import datetime


app = FastAPI()


db_models.Base.metadata.create_all(engine)


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}


def fake_hash_password(password: str):
    return "fakehashed" + password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None


class UserInDB(User):
    hashed_password: str


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def fake_decode_token(token):
    user = get_user(fake_users_db, token)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = UserInDB(**user_dict)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": user.username, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# END DB


client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
)


@app.get("/api/get", tags=["Get"], status_code=status.HTTP_200_OK)
async def get_file(
        # *,
        response: Response,
        req_code: List[str] = Query(None),
        db: Session = Depends(get_db)
):

    query = db.query(db_models.Image).filter(db_models.Image.req_code.in_(req_code)).all()
    files_in_db = get_files_from_db_limit_offset(db, query)

    if len(files_in_db) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': 'No results'}

    response.status_code = status.HTTP_200_OK
    return files_in_db


@app.post("/api/post", tags=["Upload"], status_code=status.HTTP_200_OK)
async def upload_file(
        response: Response,
        files: List[UploadFile] = File(...),
        db: Session = Depends(get_db)
):
    req_code = str(uuid4())
    today = datetime.date.today()
    if not client.bucket_exists(f"{today}"):
        client.make_bucket(f"{today}")

    for file in files:

        full_name = f'{str(uuid4())}.jpeg'

        add_file_to_db(db, req_code=req_code, full_name=full_name, file=file)
        file_size = file.file.tell()
        client.put_object(bucket_name=f"{today}", object_name=full_name, data=file, length=file_size)
    query = db.query(db_models.Image).filter(db_models.Image.req_code == req_code).all()
    uploaded_files = get_files_from_db_limit_offset(db, query)
    response.status_code = status.HTTP_200_OK
    return uploaded_files


@app.delete("/api/delete", tags=["Delete"], status_code=status.HTTP_200_OK)
async def delete_file(
        response: Response,
        req_code: str,
        db: Session = Depends(get_db)
):
    count = db.query(db_models.Image).filter(db_models.Image.req_code == req_code).count()
    if count == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': 'No files with such code'}
    query = db.query(db_models.Image).filter(db_models.Image.req_code == req_code).all()
    deleted_files = get_files_from_db_limit_offset(db, query)
    bucket_name = get_file_from_db(db, req_code).exist_time[:10]
    print(bucket_name)
    for i in range(count):
        file_info_from_db = get_file_from_db(db, req_code)
        delete_file_from_db(db, file_info_from_db)
        client.remove_object(bucket_name=bucket_name, object_name=file_info_from_db.name)
    response.status_code = status.HTTP_200_OK
    return deleted_files
