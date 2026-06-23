import base64
import hashlib
import hmac
import json
import os
import secrets

from utils import database

SESSION_FILENAME = os.getenv("GIST_SESSION_NAME", "swjtu_session.json")


def _get_key():
    secret = os.getenv("SESSION_ENCRYPTION_KEY")
    if not secret:
        return None
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        output.extend(hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest())
        counter += 1
    return bytes(output[:length])


def _encrypt_json(data: dict) -> str | None:
    key = _get_key()
    if not key:
        print("未配置 SESSION_ENCRYPTION_KEY，无法保存登录态。")
        return None

    plaintext = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    nonce = secrets.token_bytes(16)
    stream = _keystream(key, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
    signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()

    return json.dumps({
        "version": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "payload": base64.b64encode(ciphertext).decode("ascii"),
        "hmac": base64.b64encode(signature).decode("ascii"),
    }, separators=(",", ":"))


def _decrypt_json(raw_payload: str) -> dict | None:
    key = _get_key()
    if not key:
        print("未配置 SESSION_ENCRYPTION_KEY，无法读取登录态。")
        return None

    envelope = json.loads(raw_payload)
    if envelope.get("version") != 1:
        print("登录态版本不支持，请重新初始化。")
        return None

    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["payload"])
    expected = base64.b64decode(envelope["hmac"])
    actual = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, actual):
        print("登录态校验失败，请重新初始化。")
        return None

    stream = _keystream(key, nonce, len(ciphertext))
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, stream))
    return json.loads(plaintext.decode("utf-8"))


def save_session(session_data: dict):
    payload = _encrypt_json(session_data)
    if not payload:
        return None
    return database.save_file(SESSION_FILENAME, payload)


def load_session() -> dict | None:
    raw_payload = database.get_file(SESSION_FILENAME)
    if not raw_payload:
        return None
    try:
        return _decrypt_json(raw_payload)
    except Exception as e:
        print(f"读取登录态失败: {e}")
        return None
