"""Dijital Defterim - Streamlit uygulaması.

PC ve telefon aynı adrese girer, aynı sunucuya (ve aynı veritabanına) bağlanır.
Google Drive, sunucu yeniden başladığında veri kaybolmasın diye yedek katmanıdır.
"""
import os
import io
from datetime import datetime, date as date_cls

import streamlit as st
import pandas as pd

import db
from db import CATEGORIES

st.set_page_config(page_title="Dijital Defterim", page_icon="📓", layout="centered")

# ---------- Google Drive bağlantısı (varsa) ----------
DRIVE_ENABLED = False
drive_service = None
ROOT_FOLDER_ID = None
PHOTOS_FOLDER_ID = None

try:
    import drive_sync

    if "google_oauth" in st.secrets:
        drive_service = drive_sync.get_drive_service()
        ROOT_FOLDER_ID = drive_sync.ensure_root_folder(drive_service)
        DRIVE_ENABLED = True
except Exception as e:
    DRIVE_ENABLED = False
    st.session_state.setdefault("drive_error", str(e))


@st.cache_resource
def startup_sync():
    """Sunucu ilk açıldığında Drive'dan veritabanını indirir (varsa)."""
    if DRIVE_ENABLED:
        try:
            drive_sync.download_db(drive_service, ROOT_FOLDER_ID, db.DB_PATH)
        except Exception as e:
            st.session_state.setdefault("drive_error", str(e))
    db.init_db()
    return True


startup_sync()

if DRIVE_ENABLED:
    try:
        PHOTOS_FOLDER_ID = drive_sync.ensure_photos_folder(drive_service, ROOT_FOLDER_ID)
    except Exception as e:
        DRIVE_ENABLED = False
        st.session_state["drive_error"] = str(e)


def push_to_drive():
    if DRIVE_ENABLED:
        try:
            drive_sync.upload_db(drive_service, ROOT_FOLDER_ID, db.DB_PATH)
            st.session_state["last_sync"] = datetime.now()
            st.session_state["drive_error"] = None
            return True
        except Exception as e:
            st.session_state["drive_error"] = str(e)
            return False
    return False


# ---------- Üst bilgi ----------
st.title("📓 Dijital Defterim")
if not DRIVE_ENABLED:
    st.warning(
        "☁️ Google Drive yedeklemesi yapılandırılmamış — notlar sadece bu sunucuda saklanıyor. "
        "Kalıcı yedekleme için Ayarlar sekmesindeki kurulum talimatlarına bakın."
    )
elif st.session_state.get("drive_error"):
    st.error(f"Drive senkron hatası: {st.session_state['drive_error']}")
else:
    last_sync = st.session_state.get("last_sync")
    if last_sync:
        st.caption(f"☁️ Drive'a yedeklendi — son: {last_sync.strftime('%H:%M:%S')}")

tabs = st.tabs(["📖 Defter", "☐ Bekleyen", "➕ Ekle", "📊 Analiz", "⚙️ Ayarlar"])

# ============================================================
# DEFTER (zaman çizelgesi)
# ============================================================
with tabs[0]:
    items = db.get_all_items()
    if not items:
        st.info("Henüz not yok. 'Ekle' sekmesinden başla.")
    else:
        df = pd.DataFrame(items)
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("Notlarda ara", "", key="search_timeline")
        with col2:
            cat_filter = st.multiselect(
                "Kategori", options=list(CATEGORIES.keys()),
                format_func=lambda c: f"{CATEGORIES[c]['symbol']} {CATEGORIES[c]['label']}",
                key="cat_filter_timeline",
            )
        filtered = df
        if search:
            filtered = filtered[filtered["content"].str.contains(search, case=False, na=False)]
        if cat_filter:
            filtered = filtered[filtered["category"].isin(cat_filter)]

        for d, group in filtered.groupby("date", sort=False):
            st.subheader(d)
            for _, row in group.iterrows():
                meta = CATEGORIES.get(row["category"], CATEGORIES["note"])
                cols = st.columns([0.5, 4, 1, 1])
                with cols[0]:
                    checked = st.checkbox("Tamamlandı", value=bool(row["completed"]), key=f"chk_{row['id']}", label_visibility="collapsed")
                    if checked != bool(row["completed"]):
                        db.toggle_complete(row["id"], checked)
                        push_to_drive()
                        st.rerun()
                    st.caption(meta["symbol"])
                with cols[1]:
                    text = row["content"]
                    if row["item_time"]:
                        text = f"`{row['item_time']}` {text}"
                    if row["completed"]:
                        st.markdown(f"~~{text}~~")
                    else:
                        st.markdown(text)
                    if row["completed"] and row["completed_at"] and row["created_at"]:
                        created = datetime.fromisoformat(row["created_at"])
                        completed_dt = datetime.fromisoformat(row["completed_at"])
                        hours = (completed_dt - created).total_seconds() / 3600
                        st.caption(f"✓ {db.format_duration(hours)} içinde tamamlandı")
                with cols[2]:
                    if row["photo_drive_id"] and DRIVE_ENABLED:
                        if st.button("📷", key=f"photo_{row['id']}"):
                            img_bytes = drive_sync.download_photo_bytes(drive_service, row["photo_drive_id"])
                            st.session_state[f"show_photo_{row['id']}"] = img_bytes
                        if st.session_state.get(f"show_photo_{row['id']}"):
                            st.image(st.session_state[f"show_photo_{row['id']}"])
                with cols[3]:
                    if st.button("🗑", key=f"del_{row['id']}"):
                        db.delete_item(row["id"])
                        push_to_drive()
                        st.rerun()

# ============================================================
# BEKLEYEN GÖREVLER
# ============================================================
with tabs[1]:
    items = db.get_all_items()
    pending = [it for it in items if not it["completed"]]
    now = datetime.now()
    for it in pending:
        created = datetime.fromisoformat(it["created_at"])
        it["_waiting_hours"] = (now - created).total_seconds() / 3600
    pending.sort(key=lambda x: -x["_waiting_hours"])  # en uzun süredir bekleyen en üstte — kronik konuları göstermek için
    st.caption(f"{len(pending)} tamamlanmamış görev — en uzun süredir bekleyen en üstte")
    if not pending:
        st.success("Bekleyen görev yok — hepsi tamam! 🎉")
    selected_ids = []
    for it in pending:
        cols = st.columns([0.5, 4, 1.5])
        with cols[0]:
            sel = st.checkbox("Seç", key=f"sel_{it['id']}", label_visibility="collapsed")
            if sel:
                selected_ids.append(it["id"])
        with cols[1]:
            st.write(it["content"])
            st.caption(it["date"])
        with cols[2]:
            waiting = it["_waiting_hours"]
            color = "red" if waiting > 72 else ("orange" if waiting > 24 else "gray")
            st.markdown(f":{color}[{db.format_duration(waiting)}dır bekliyor]")

    if selected_ids:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"✓ {len(selected_ids)} tanesini tamamlandı işaretle"):
                db.bulk_complete(selected_ids)
                push_to_drive()
                st.rerun()
        with c2:
            if st.button(f"🗑 {len(selected_ids)} tanesini sil"):
                db.delete_items(selected_ids)
                push_to_drive()
                st.rerun()

# ============================================================
# EKLE
# ============================================================
with tabs[2]:
    st.subheader("Yeni not ekle")

    draft = st.session_state.get("draft")

    if draft is None:
        # --- Adım 1: notu yaz ---
        content = st.text_area("Notunu yaz — kategoriyi program senin yerine tahmin edecek", key="new_note_content")
        photo_camera = st.camera_input("Kamerayla çek (opsiyonel)")
        photo_upload = st.file_uploader("ya da galeriden seç (opsiyonel)", type=["jpg", "jpeg", "png"])

        if st.button("Devam et →", disabled=not content.strip()):
            detected = db.detect_category(content)
            photo_file = photo_camera or photo_upload
            st.session_state["draft"] = {
                "content": content.strip(),
                "category": detected,
                "date": date_cls.today(),
                "photo_bytes": photo_file.getvalue() if photo_file is not None else None,
            }
            st.rerun()

    else:
        # --- Adım 2: onay ekranı ---
        st.info("Kaydetmeden önce kontrol et — kategori tahminidir, gerekirse değiştir.")
        st.markdown(f"**Not:** {draft['content']}")

        cat_keys = list(CATEGORIES.keys())
        default_idx = cat_keys.index(draft["category"]) if draft["category"] in cat_keys else 0
        chosen_category = st.selectbox(
            "Kategori (tahmin edildi, istersen değiştir)",
            options=cat_keys,
            index=default_idx,
            format_func=lambda c: f"{CATEGORIES[c]['symbol']} {CATEGORIES[c]['label']}",
        )
        chosen_date = st.date_input("Tarih", value=draft["date"])

        avg_hours = db.predict_duration_for_category(chosen_category)
        if avg_hours is not None:
            st.caption(f"ℹ️ Bu kategorideki notlar geçmişte ortalama **{db.format_duration(avg_hours)}** içinde tamamlanmış.")

        if draft.get("photo_bytes"):
            st.image(draft["photo_bytes"], width=200)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✕ Vazgeç"):
                del st.session_state["draft"]
                st.rerun()
        with col2:
            if st.button("✓ Onayla ve kaydet", type="primary"):
                photo_drive_id = None
                if draft["photo_bytes"] and DRIVE_ENABLED:
                    fname = f"{chosen_date}_{datetime.now().strftime('%H%M%S')}.jpg"
                    photo_drive_id = drive_sync.upload_photo(drive_service, PHOTOS_FOLDER_ID, draft["photo_bytes"], fname)
                elif draft["photo_bytes"]:
                    st.warning("Fotoğraf çekildi ama Drive bağlı olmadığı için kalıcı saklanamıyor.")

                db.add_item(
                    item_date=chosen_date,
                    category=chosen_category,
                    content=draft["content"],
                    photo_drive_id=photo_drive_id,
                )
                push_to_drive()
                del st.session_state["draft"]
                st.success("Kaydedildi.")
                st.rerun()

# ============================================================
# ANALİZ
# ============================================================
with tabs[3]:
    items = db.get_all_items()
    if not items:
        st.info("Analiz için henüz veri yok.")
    else:
        df = pd.DataFrame(items)
        completed = df[df["completed"] == 1]
        completion_rate = round(100 * len(completed) / len(df)) if len(df) else 0

        # Tamamlanan görevler için süre hesapla
        completed = completed.copy()
        if not completed.empty:
            completed["created_dt"] = pd.to_datetime(completed["created_at"])
            completed["completed_dt"] = pd.to_datetime(completed["completed_at"])
            completed["duration_h"] = (completed["completed_dt"] - completed["created_dt"]).dt.total_seconds() / 3600
        avg_hours = completed["duration_h"].mean() if not completed.empty else None

        c1, c2, c3 = st.columns(3)
        c1.metric("Tamamlanma oranı", f"%{completion_rate}")
        c2.metric("Ort. tamamlama süresi", db.format_duration(avg_hours))
        c3.metric("Toplam not", len(df))

        st.subheader("Kategori dağılımı")
        cat_counts = df["category"].value_counts()
        cat_counts.index = [f"{CATEGORIES[c]['symbol']} {CATEGORIES[c]['label']}" for c in cat_counts.index]
        st.bar_chart(cat_counts)

        st.subheader("Kategoriye göre ortalama tamamlama süresi")
        avg_by_cat = db.avg_duration_by_category()
        if not avg_by_cat:
            st.caption("Henüz tamamlanmış görev yok, bu grafik veri birikince dolacak.")
        else:
            avg_series = pd.Series(
                {f"{CATEGORIES[c]['symbol']} {CATEGORIES[c]['label']}": h for c, h in avg_by_cat.items()}
            ).sort_values(ascending=False)
            st.bar_chart(avg_series)

        st.subheader("⏱ Zaman içinde tamamlama sayısı (haftalık)")
        if not completed.empty:
            weekly = completed.set_index("completed_dt").resample("W").size()
            st.bar_chart(weekly)
        else:
            st.caption("Henüz tamamlanmış görev yok.")

        st.subheader("🔥 Kronik konular (en uzun süredir bekleyenler)")
        pending = df[df["completed"] == 0].copy()
        if pending.empty:
            st.success("Bekleyen görev yok.")
        else:
            pending["created_dt"] = pd.to_datetime(pending["created_at"])
            pending["bekleme_saat"] = (pd.Timestamp.now() - pending["created_dt"]).dt.total_seconds() / 3600
            pending = pending.sort_values("bekleme_saat", ascending=False).head(5)
            pending["Bekliyor"] = pending["bekleme_saat"].apply(db.format_duration)
            st.dataframe(pending[["date", "content", "Bekliyor"]], hide_index=True)
            st.caption("Bir konu burada uzun süre kalıyorsa, muhtemelen tekrar eden/çözülemeyen bir sorundur.")

# ============================================================
# AYARLAR
# ============================================================
with tabs[4]:
    st.subheader("Google Drive yedekleme")
    if DRIVE_ENABLED:
        st.success("Drive bağlantısı aktif.")
        if st.button("Şimdi Drive'a yedekle"):
            if push_to_drive():
                st.success("Yedeklendi.")
            else:
                st.error(f"Yedekleme başarısız: {st.session_state.get('drive_error')}")
    else:
        st.error("Drive bağlı değil.")
        if st.session_state.get("drive_error"):
            st.code(st.session_state["drive_error"], language=None)
        with st.expander("Nasıl kurulur?"):
            st.markdown(
                """
                **Not:** Servis hesabı YÖNTEMİ artık kullanılmıyor — Google, servis
                hesaplarına depolama kotası vermiyor. Bunun yerine kendi Google
                hesabınla (OAuth) bir kere izin veriyorsun.

                1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services → Credentials**
                   → **+ CREATE CREDENTIALS → OAuth client ID** → Application type: **Desktop app** → oluştur.
                2. Açılan pencereden **JSON'u indir**, `oauth_client_secret.json` adıyla proje klasörüne koy.
                3. Terminalde proje klasöründeyken şunu çalıştır:
                ```
                python authorize_drive.py
                ```
                4. Tarayıcı açılır, kendi Google hesabınla giriş yap, izin ver.
                5. Terminale basılan `[google_oauth]` bloğunu kopyalayıp
                   `.streamlit/secrets.toml` dosyana yapıştır.
                6. Uygulamayı yeniden başlat.

                Streamlit Cloud'a deploy ettiğinde, aynı bloğu oradaki
                **Settings → Secrets** kısmına da yapıştırman yeterli.
                """
            )

    st.divider()
    st.subheader("Dosya olarak yedekle")
    items = db.get_all_items()
    if items:
        df = pd.DataFrame(items)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV olarak indir", csv, "dijital-defterim-yedek.csv", "text/csv")
