import os
import subprocess
import sys
from pathlib import Path
import bcrypt
import pytest
from auth.utils import get_password_hash, verify_password, create_access_token, verify_token


@pytest.mark.parametrize('password', ['ordinary-password', '密' * 100, 'a' * 100])
def test_password_hash_roundtrip(password):
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password(password + 'x', hashed)
    assert get_password_hash(password) != hashed


def test_existing_bcrypt_records_still_work():
    hashed = bcrypt.hashpw(b'old-password', bcrypt.gensalt()).decode()
    assert verify_password('old-password', hashed)
    assert not verify_password('wrong-password', hashed)


def test_unknown_or_corrupted_hash_is_rejected():
    assert not verify_password('password', 'scrypt$broken$hash')
    assert not verify_password('password', 'unknown')


def test_tokens_roundtrip_and_tampering_is_rejected():
    token = create_access_token({'sub': '1'})
    assert verify_token(token)['sub'] == '1'
    assert verify_token(token + 'tampered') is None


@pytest.mark.parametrize('key', ['', 'short', 'poker-llm-secret-key-change-in-production-2024'])
def test_production_rejects_missing_or_known_secret(key):
    env = dict(os.environ, APP_ENV='production', JWT_SECRET_KEY=key,
        PYTHONPATH=str(Path(__file__).resolve().parent.parent / 'backend'))
    proc = subprocess.run([sys.executable, '-c', 'import settings'], env=env, capture_output=True)
    assert proc.returncode != 0
    assert b'Production requires' in proc.stderr
