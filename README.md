# Dijital Defterim (Streamlit)

Gerçek Python + Streamlit uygulaması. PC ve telefon aynı web adresine girer,
aynı sunucuya bağlanır — bu yüzden aynı WiFi şartı yoktur (uygulama buluta
deploy edildiğinde).

## 1) Yerelde test et

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır. Bu aşamada Google Drive
bağlı değildir, notlar sadece bilgisayarındaki `notdefterim.db` dosyasında
durur — bu tamamen normal, önce temel işlevleri test et.

## 2) GitHub'a yükle

1. [github.com](https://github.com) üzerinde ücretsiz bir hesap aç (yoksa).
2. Yeni bir repo oluştur (ör. `dijital-defterim`), bu klasördeki tüm dosyaları
   (özellikle `app.py`, `db.py`, `drive_sync.py`, `requirements.txt`) oraya yükle.
   **`.streamlit/secrets.toml` dosyasını ASLA GitHub'a yükleme** — sadece
   `secrets.toml.example` yüklenmeli, gerçek anahtarlar Streamlit Cloud'un
   kendi "Secrets" ayarına girilecek.

## 3) Google Drive bağlantısını kur (kalıcı yedekleme + senkron için)

**Önemli:** Servis hesabı yöntemi kullanılmıyor — Google, servis hesaplarına
depolama kotası vermiyor (2023'ten beri geçerli bir politika), bu yüzden
dosya oluşturma/güncelleme işlemleri her zaman "kota yok" hatası verir.
Bunun yerine kendi Google hesabınla (OAuth) bir kere izin veriyorsun;
dosyalar senin kendi Drive kotana yazılır.

1. [Google Cloud Console](https://console.cloud.google.com/) üzerinde
   (Google Drive API zaten etkinse) **APIs & Services → Credentials**'a git.
2. **+ CREATE CREDENTIALS → OAuth client ID** → Application type olarak
   **Desktop app** seç → oluştur.
3. Açılan pencereden JSON dosyasını indir, adını `oauth_client_secret.json`
   yap ve proje klasörüne (app.py ile aynı yere) koy.
4. Terminalde proje klasöründeyken (venv aktifken) şunu çalıştır:
   ```
   python authorize_drive.py
   ```
5. Bir tarayıcı sekmesi açılacak — kendi Google hesabınla giriş yap,
   "Bu uygulama doğrulanmadı" uyarısı çıkarsa "Gelişmiş → yine de devam et"
   de (kendi oluşturduğun uygulama olduğu için güvenlidir), izin ver.
6. Terminale basılan `[google_oauth]` bloğunu kopyala, proje klasöründeki
   `.streamlit/secrets.toml` dosyasına yapıştır (dosya yoksa oluştur).
7. Uygulamayı yeniden başlat — Ayarlar sekmesinde "Drive bağlantısı aktif"
   yazmalı.

## 4) Streamlit Community Cloud'a deploy et

1. [share.streamlit.io](https://share.streamlit.io/) adresine GitHub
   hesabınla giriş yap.
2. "New app" → GitHub reponu seç → ana dosya olarak `app.py` seç → Deploy.
3. Deploy olduktan sonra **Settings → Secrets** kısmına, `authorize_drive.py`
   çalıştırdığında terminale basılan `[google_oauth]` bloğunun AYNISINI
   yapıştır:

```toml
[google_oauth]
client_id = "....apps.googleusercontent.com"
client_secret = "..."
refresh_token = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

4. Kaydet — uygulama yeniden başlar ve artık Drive'a bağlıdır.

## 5) Telefondan eriş

Streamlit Cloud sana `https://kullaniciadi-dijital-defterim.streamlit.app`
gibi bir adres verir. Bu adresi telefonunda da açman yeterli — WiFi'dan
bağımsız, her yerden çalışır, çünkü PC ve telefon aynı sunucuya bağlanıyor.

## Notlar

- Şu an fotoğraftan otomatik not okuma (AI) yok — sadece kamera/galeri
  fotoğrafı ekleyip notunla birlikte saklayabiliyorsun. İstersen ileride
  bir Anthropic API anahtarıyla bu özelliği ekleyebiliriz.
- Streamlit Cloud'un ücretsiz planı, uzun süre kullanılmayan uygulamaları
  "uyku" moduna alabilir — ilk açılışta birkaç saniye beklemen gerekebilir.
