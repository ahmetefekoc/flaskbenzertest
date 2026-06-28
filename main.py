from flask import Flask, request, jsonify, render_template_string
import imagehash
from PIL import Image
import io
import json
import os

app = Flask(__name__)

HASH_FILE = "banned_hashes.json"

def load_hashes():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE) as f:
            return json.load(f)
    return []

HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hash Karşılaştırıcı</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #222535;
    --border: #2e3147;
    --accent: #5865f2;
    --accent-dim: rgba(88,101,242,0.15);
    --text: #e8eaf0;
    --muted: #7880a0;
    --danger: #ed4245;
    --warn: #f0a932;
    --ok: #3ba55c;
    --radius: 12px;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 48px 16px;
  }

  .wrap { width: 100%; max-width: 680px; }

  header { margin-bottom: 36px; }
  header h1 {
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: var(--text);
  }
  header p { color: var(--muted); font-size: 13px; margin-top: 4px; }

  /* Drop zone */
  .drop {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 48px 24px;
    text-align: center;
    cursor: pointer;
    transition: border-color .2s, background .2s;
    position: relative;
  }
  .drop:hover, .drop.over {
    border-color: var(--accent);
    background: var(--accent-dim);
  }
  .drop input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .drop-icon { font-size: 32px; margin-bottom: 12px; }
  .drop p { color: var(--muted); font-size: 13px; }
  .drop strong { color: var(--text); }

  /* Preview */
  #preview-wrap {
    display: none;
    margin-top: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    align-items: center;
    gap: 16px;
  }
  #preview-wrap.show { display: flex; }
  #preview-img {
    width: 80px; height: 80px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid var(--border);
  }
  #preview-name { font-size: 13px; color: var(--muted); margin-top: 2px; }

  /* Button */
  button {
    margin-top: 20px;
    width: 100%;
    padding: 13px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s, transform .1s;
  }
  button:hover { opacity: .9; }
  button:active { transform: scale(.99); }
  button:disabled { opacity: .4; cursor: default; }

  /* Results */
  #results { margin-top: 28px; }

  .verdict {
    padding: 16px 20px;
    border-radius: var(--radius);
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .verdict.ban  { background: rgba(237,66,69,.12); border: 1px solid rgba(237,66,69,.3); color: var(--danger); }
  .verdict.safe { background: rgba(59,165,92,.10); border: 1px solid rgba(59,165,92,.3); color: var(--ok); }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    margin-bottom: 10px;
  }
  .card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .hash-label { font-size: 12px; color: var(--muted); font-family: monospace; }
  .badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: .5px;
  }
  .badge.ban  { background: rgba(237,66,69,.15); color: var(--danger); }
  .badge.warn { background: rgba(240,169,50,.15); color: var(--warn); }
  .badge.safe { background: rgba(59,165,92,.12); color: var(--ok); }

  /* Progress bar */
  .bar-wrap {
    background: var(--surface2);
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    border-radius: 99px;
    transition: width .4s ease;
  }
  .bar.danger { background: var(--danger); }
  .bar.warn   { background: var(--warn); }
  .bar.ok     { background: var(--ok); }

  .similarity-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: var(--muted);
    margin-top: 6px;
  }
  .similarity-val { font-weight: 700; font-size: 14px; }
  .similarity-val.danger { color: var(--danger); }
  .similarity-val.warn   { color: var(--warn); }
  .similarity-val.ok     { color: var(--ok); }

  /* Spinner */
  .spinner {
    display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,.2);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin .7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .empty { color: var(--muted); font-size: 13px; text-align: center; padding: 32px 0; }

  .hash-count {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 16px;
  }
  .hash-count span { color: var(--text); font-weight: 600; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🔍 Hash Karşılaştırıcı</h1>
    <p>Yüklenen görseli yasaklı hash listesiyle karşılaştırır</p>
  </header>

  <div class="drop" id="drop">
    <input type="file" id="file-input" accept="image/*">
    <div class="drop-icon">🖼️</div>
    <p><strong>Görseli buraya sürükle</strong> veya tıkla</p>
    <p style="margin-top:4px;font-size:12px">PNG, JPG, WEBP desteklenir</p>
  </div>

  <div id="preview-wrap">
    <img id="preview-img" src="" alt="önizleme">
    <div>
      <div id="preview-name"></div>
    </div>
  </div>

  <button id="btn" disabled onclick="compare()">Karşılaştır</button>

  <div id="results"></div>
</div>

<script>
const drop = document.getElementById('drop');
const fileInput = document.getElementById('file-input');
const btn = document.getElementById('btn');
let selectedFile = null;

fileInput.addEventListener('change', e => setFile(e.target.files[0]));

drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => {
  e.preventDefault(); drop.classList.remove('over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});

function setFile(f) {
  if (!f) return;
  selectedFile = f;
  btn.disabled = false;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('preview-img').src = ev.target.result;
    document.getElementById('preview-name').textContent = f.name;
    document.getElementById('preview-wrap').classList.add('show');
  };
  reader.readAsDataURL(f);
  document.getElementById('results').innerHTML = '';
}

async function compare() {
  if (!selectedFile) return;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Karşılaştırılıyor…';

  const form = new FormData();
  form.append('image', selectedFile);

  try {
    const res = await fetch('/compare', { method: 'POST', body: form });
    const data = await res.json();
    renderResults(data);
  } catch(e) {
    document.getElementById('results').innerHTML = '<p style="color:var(--danger)">Hata oluştu.</p>';
  }

  btn.disabled = false;
  btn.textContent = 'Tekrar Karşılaştır';
}

function renderResults(data) {
  const el = document.getElementById('results');
  if (data.error) { el.innerHTML = `<p style="color:var(--danger)">${data.error}</p>`; return; }

  const results = data.results;
  const isBanned = results.some(r => r.similarity >= 90);
  const isWarn   = !isBanned && results.some(r => r.similarity >= 70);

  let html = '';

  // Verdict
  if (isBanned) {
    html += `<div class="verdict ban">🚫 Bu görsel yasaklı — Bot banlar</div>`;
  } else if (isWarn) {
    html += `<div class="verdict" style="background:rgba(240,169,50,.10);border:1px solid rgba(240,169,50,.3);color:var(--warn)">⚠️ Şüpheli benzerlik — İncelenmeli</div>`;
  } else {
    html += `<div class="verdict safe">✅ Temiz — Yasaklı görsellerle eşleşme yok</div>`;
  }

  html += `<div class="hash-count">Karşılaştırılan hash sayısı: <span>${results.length}</span></div>`;

  results.forEach((r, i) => {
    const s = r.similarity;
    const cls = s >= 90 ? 'danger' : s >= 70 ? 'warn' : 'ok';
    const badge = s >= 90 ? 'ban' : s >= 70 ? 'warn' : 'safe';
    const badgeText = s >= 90 ? 'Eşleşti' : s >= 70 ? 'Şüpheli' : 'Temiz';

    html += `
    <div class="card">
      <div class="card-top">
        <span class="hash-label">#${i+1} — ${r.hash}</span>
        <span class="badge ${badge}">${badgeText}</span>
      </div>
      <div class="bar-wrap">
        <div class="bar ${cls}" style="width:${s}%"></div>
      </div>
      <div class="similarity-row">
        <span>Benzerlik</span>
        <span class="similarity-val ${cls}">${s.toFixed(1)}%</span>
      </div>
    </div>`;
  });

  el.innerHTML = html;
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/compare", methods=["POST"])
def compare():
    if "image" not in request.files:
        return jsonify({"error": "Görsel bulunamadı."}), 400

    file = request.files["image"]
    try:
        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        uploaded_hash = imagehash.phash(img)
    except Exception:
        return jsonify({"error": "Görsel okunamadı."}), 400

    banned = load_hashes()
    if not banned:
        return jsonify({"error": "banned_hashes.json bulunamadı veya boş."}), 400

    results = []
    for h in banned:
        stored = imagehash.hex_to_hash(h)
        diff = uploaded_hash - stored          # 0 = birebir aynı, 64 = tamamen farklı
        similarity = max(0, (64 - diff) / 64 * 100)
        results.append({"hash": h, "diff": diff, "similarity": round(similarity, 2)})

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True, port=5000)