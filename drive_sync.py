"""Dijital Defterim - Google Drive senkron/yedekleme katmanı.

Kullanıcının KENDİ Google hesabıyla (OAuth) çalışır — servis hesabı DEĞİL.
Servis hesaplarının Google tarafından hiç depolama kotası verilmediği için
(2023'ten beri geçerli bir politika), dosyalar kullanıcının kendi hesabının
kotasına yazılır. Bunun için önce bir kere `authorize_drive.py` çalıştırılıp
kalıcı bir refresh_token elde edilmesi gerekir (README'ye bakın).
"""
import io
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2.credentials import Credentials

DB_FILENAME = "notdefterim.db"
ROOT_FOLDER_NAME = "NotDefterimVerileri"
PHOTOS_FOLDER_NAME = "fotograflar"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


@st.cache_resource
def get_drive_service():
    o = st.secrets["google_oauth"]
    creds = Credentials(
        token=None,
        refresh_token=o["refresh_token"],
        client_id=o["client_id"],
        client_secret=o["client_secret"],
        token_uri=o.get("token_uri", "https://oauth2.googleapis.com/token"),
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def _find_file(service, name, parent_id=None, mime_type=None):
    q = f"name = '{name}' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    if mime_type:
        q += f" and mimeType = '{mime_type}'"
    res = service.files().list(q=q, fields="files(id, name)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def ensure_root_folder(service):
    folder_id = _find_file(service, ROOT_FOLDER_NAME, mime_type="application/vnd.google-apps.folder")
    if folder_id:
        return folder_id
    metadata = {"name": ROOT_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def ensure_photos_folder(service, root_folder_id):
    folder_id = _find_file(service, PHOTOS_FOLDER_NAME, parent_id=root_folder_id, mime_type="application/vnd.google-apps.folder")
    if folder_id:
        return folder_id
    metadata = {
        "name": PHOTOS_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [root_folder_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def download_db(service, root_folder_id, local_path=DB_FILENAME):
    file_id = _find_file(service, DB_FILENAME, parent_id=root_folder_id)
    if not file_id:
        return False
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.close()
    return True


def upload_db(service, root_folder_id, local_path=DB_FILENAME):
    file_id = _find_file(service, DB_FILENAME, parent_id=root_folder_id)
    media = MediaIoBaseUpload(io.FileIO(local_path, "rb"), mimetype="application/x-sqlite3", resumable=True)
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": DB_FILENAME, "parents": [root_folder_id]}
        service.files().create(body=metadata, media_body=media, fields="id").execute()


def upload_photo(service, photos_folder_id, file_bytes, filename, mimetype="image/jpeg"):
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=True)
    metadata = {"name": filename, "parents": [photos_folder_id]}
    f = service.files().create(body=metadata, media_body=media, fields="id").execute()
    return f["id"]


def download_photo_bytes(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()
