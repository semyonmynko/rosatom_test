import os
from datetime import datetime

import db_models


# Get file info from DBx
def get_file_from_db(db, req_code):
    return db.query(db_models.Image).filter(db_models.Image.req_code == req_code).first()


# Offset\limit
def get_files_from_db_limit_offset(db, query, limit: int = None, offset: int = None):
    if limit and not offset:
        query = query[:limit]
    elif limit and offset:
        limit += offset
        query = query[offset:limit]
    elif not limit and offset:
        query = query[offset:]
    return query


# Add File to DB
def add_file_to_db(db, **kwargs):
    new_file = db_models.Image(
                                req_code=kwargs['req_code'],
                                name=kwargs['full_name'],
                                exist_time=datetime.now()
                            )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


# Delete file from DB
def delete_file_from_db(db, file_info_from_db):
    db.delete(file_info_from_db)
    db.commit()

