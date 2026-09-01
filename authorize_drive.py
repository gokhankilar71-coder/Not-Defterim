"""Bir kerelik kurulum betiği: kendi Google hesabınla Drive'a izin ver.

Bu betiği SADECE BİR KERE, kendi bilgisayarında çalıştırman yeterli.
Çalıştığında tarayıcı açılır, kendi Google hesabınla giriş yapıp izin
verirsin. Sonunda ekrana basılan metni ".streamlit/secrets.toml" dosyana
kopyala — ondan sonra hem yerel hem de Streamlit Cloud'daki uygulama bu
izinle Drive'a yazabilir.

Kullanım:
    python authorize_drive.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

if __name__ == "__main__":
    flow = InstalledAppFlow.from_client_secrets_file("oauth_client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n\n=== Aşağıdaki metni .streamlit/secrets.toml dosyana yapıştır ===\n")
    print("[google_oauth]")
    print(f'client_id = "{creds.client_id}"')
    print(f'client_secret = "{creds.client_secret}"')
    print(f'refresh_token = "{creds.refresh_token}"')
    print(f'token_uri = "{creds.token_uri}"')
    print("\n=== (buraya kadar) ===\n")
