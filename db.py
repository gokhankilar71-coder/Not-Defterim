"""Dijital Defterim - SQLite veritabanı katmanı."""
import sqlite3
import uuid
from datetime import datetime, date as date_cls

DB_PATH = "notdefterim.db"

CATEGORIES = {
    "task": {"label": "Görev", "symbol": "☐"},
    "meeting": {"label": "Toplantı", "symbol": "Δ"},
    "deadline": {"label": "Kritik/Son tarih", "symbol": "!"},
    "important": {"label": "Önemli", "symbol": "✶"},
    "explore": {"label": "Araştır", "symbol": "?"},
    "idea": {"label": "Fikir", "symbol": "♡"},
    "message": {"label": "İletişim/Arama", "symbol": "✉"},
    "domestic": {"label": "Kişisel", "symbol": "⌂"},
    "note": {"label": "Not", "symbol": "·"},
}

# Anahtar kelime tabanlı otomatik kategori tespiti.
# Not: Bu bir yapay zeka değil, basit bir kelime eşleştirme kuralıdır —
# yanlış tahmin edebilir, bu yüzden kaydetmeden önce kullanıcıya onaylatılır.
CATEGORY_KEYWORDS = {
    "deadline": ["son tarih", "e kadar", "'e kadar", "acil", "kritik", "gecikme", "bitmeli"],
    "meeting": ["toplantı", "görüş", "buluş", "meeting"],
    "explore": ["araştır", "incele", "sorgula", "test edilecek", "kontrol edilecek", "bakılacak"],
    "message": ["ara ", "arayacak", "mail at", "haber ver", "bilgi ver", "söyle", "iletişime geç", "temsilcisi"],
    "important": ["önemli", "dikkat"],
    "domestic": ["ev işi", "market", "fatura", "kişisel"],
    "idea": ["fikir", "öneri", "olabilir mi"],
    "task": ["yap", "tamamla", "bitir", "kur", "değiştir", "monte", "bakım", "onar", "montaj"],
}
CATEGORY_PRIORITY = ["deadline", "meeting", "explore", "message", "important", "domestic", "idea", "task"]


def detect_category(content):
    text = content.lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(CATEGORY_PRIORITY, key=lambda c: (scores[c], -CATEGORY_PRIORITY.index(c)))
    if scores[best] == 0:
        return "task"  # hiçbir anahtar kelime eşleşmediyse varsayılan
    return best


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            item_time TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            photo_drive_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_item(item_date, category, content, photo_drive_id=None):
    conn = get_conn()
    item_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO items (id, date, category, content, item_time, due_date, completed, completed_at, photo_drive_id, created_at)
           VALUES (?, ?, ?, ?, NULL, NULL, 0, NULL, ?, ?)""",
        (item_id, str(item_date), category, content, photo_drive_id, now),
    )
    conn.commit()
    conn.close()
    return item_id


def get_all_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_complete(item_id, completed):
    conn = get_conn()
    completed_at = datetime.now().isoformat() if completed else None
    conn.execute("UPDATE items SET completed=?, completed_at=? WHERE id=?", (1 if completed else 0, completed_at, item_id))
    conn.commit()
    conn.close()


def update_item(item_id, **fields):
    if not fields:
        return
    conn = get_conn()
    cols = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [item_id]
    conn.execute(f"UPDATE items SET {cols} WHERE id=?", values)
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_conn()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def delete_items(item_ids):
    conn = get_conn()
    conn.executemany("DELETE FROM items WHERE id=?", [(i,) for i in item_ids])
    conn.commit()
    conn.close()


def bulk_complete(item_ids):
    conn = get_conn()
    now = datetime.now().isoformat()
    conn.executemany("UPDATE items SET completed=1, completed_at=? WHERE id=?", [(now, i) for i in item_ids])
    conn.commit()
    conn.close()


# ---------- Süre analizi ----------
def format_duration(hours):
    """Saat cinsinden bir süreyi 'X gün Y saat' gibi okunabilir hale getirir."""
    if hours is None:
        return "—"
    if hours < 1:
        return f"{max(1, round(hours * 60))} dk"
    if hours < 24:
        return f"{round(hours)} saat"
    days = hours / 24
    return f"{days:.1f} gün"


def avg_duration_by_category():
    """Her kategori için ortalama tamamlanma süresini (saat) döner."""
    items = get_all_items()
    from collections import defaultdict
    sums = defaultdict(float)
    counts = defaultdict(int)
    for it in items:
        if it["completed"] and it["completed_at"] and it["created_at"]:
            created = datetime.fromisoformat(it["created_at"])
            completed = datetime.fromisoformat(it["completed_at"])
            hours = (completed - created).total_seconds() / 3600
            sums[it["category"]] += hours
            counts[it["category"]] += 1
    return {cat: (sums[cat] / counts[cat]) for cat in counts}


def predict_duration_for_category(category):
    avgs = avg_duration_by_category()
    return avgs.get(category)

