import requests


def test_post():
    req = requests.get('http://127.0.0.1:8000/api/post?req_code=228')
    assert req.status_code


def test_get():
    req = requests.get('http://127.0.0.1:8000/api/get?req_code=24c0302d-8016-45f2-adf0-4a902a4f3afb')
    assert req.status_code == 200


def test_delete():
    req = requests.get('http://127.0.0.1:8000/api/delete?req_code=24c0302d-8016-45f2-adf0-4a902a4f3afb')
    assert req.status_code
