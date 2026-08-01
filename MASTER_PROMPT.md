# GÖREV: Tower of Babel'i oynanabilir ürüne tamamla (otonom)

Proje yolu: ~/tower-of-babel
Ben (geliştirici), RULES.md §0'daki STANDING DIRECTIVE ile Faz 11→15'i
otonom tamamlaman için ön onay verdim. Oynanabilir oyun yokken denge
yazılmayacak — içerik/denge onayı oyun oynanabilir olduktan SONRA yapılacak.

## Talimatlar

1. Önce `tower-of-babel` skill'ini yükle (skill_view).
2. Sırasıyla oku: RULES.md (§0 dahil) → docs/development/STATUS.md →
   IMPLEMENTATION_PLAN.md → docs/development/VERTICAL_SLICE.md →
   docs/design/DESIGN_DECISIONS.md → docs/architecture/ARCHITECTURE.md.
3. IMPLEMENTATION_PLAN.md'deki detaylı faz bölümlerine göre sırayla
   ilerle, atlama yok:
   - Faz 11 — VILLAGE FRAMEWORK (src/gameplay/village/, 3 bina arsası,
     2 görsel kademe, Town Level + bina seviyeleri, run sonucu uygulama)
   - Faz 12 — NPC FRAMEWORK (3 servis NPC'si: loadout / run hazırlığı /
     yükseltme, servis kademesi ilerlemesi, milestone ile geliş, diyalog veri
     olarak)
   - Faz 13 — PERSISTENT PROGRESSION (class mastery L13, unlock motoru,
     rekorlar, run başında kalıcı bonuslar L15)
   - Faz 14 — SAVE/LOAD ENTEGRASYONU (src/save, slot yönetimi, D15 geçici
     politikası: köyde kayıt + oda geçişlerinde run checkpoint, bozuk kayıt
     koruması, tam roundtrip testleri)
   - Faz 15 — VERTICAL SLICE ENTEGRASYONU (menü → köy → hazırlık → zindan
     5 kat: 4 üretilmiş + boss → boss → ölüm/dönüş → köy yükseltmesi → NPC
     kademesi → yeni run'da yeni seçenekler. Headless tam-run entegrasyon
     testi yaz. BURASI OYNANABİLİR ÜRÜN KAPISI — bitince DUR ve raporla.)
4. Açık tasarım kararları için GEÇİCİ varsayılanlar (RULES.md §0'da yazılı):
   D3-tek kahraman/sınıf değiştirme · D7-mevcut oda-grafı navigasyonu ·
   D14-choice-of-3 boons · D15-köy kaydı + oda checkpoint'i.
5. Kısıtlar: SADECE greybox placeholder içerik (nötr isimler, renkli
   dikdörtgenler). Tema/lore/final içerik YOK. Denge ayarı YOK — mevcut
   varsayılanlar aynen kalsın. Data-driven YAML, magic value yok, adapter
   izolasyonu, EventBus. Faz 16+ (içerik/polish/QA/release) BAŞLATMA.
6. Her fazda AI DEVELOPMENT LOOP'u izle; her faz bitince 5 doğrulama
   komutunu çalıştır:
   uv run pytest -q
   uv run ruff check src tests tools scripts
   uv run python -m mypy src
   uv run python tools/data_validation/validate_data.py
   uv run python scripts/run.py --headless --frames 300 --log-level WARNING
   uv run python scripts/run.py --headless --combat-test --frames 300 --log-level WARNING
7. Her fazı ayrı commit'le (feat:/fix:/test:/docs:), STATUS.md + plan
   snapshot + CHANGELOG.md aynı commit'te güncelle. Remote'a push'la.
8. Context şişmesine karşı: her faz sonunda commit'le; gerekirse
   STATUS.md'yi checkpoint olarak kullan, yeniden okumayı minimize et.
9. BİTİRİNCE (Faz 15 sonrası): Türkçe, kısa ve pratik son rapor ver:
   - Oynanabilir olan ne (loop: menü→köy→zindan→boss→dönüş→yükseltme→yeni run)
   - Kontroller
   - Doğrulama sonuçları (test sayıları, ruff/mypy, headless exit 0)
   - Ertelenenler (açık tasarım kararları, teknik borç, insan onayı gerekenler)
   - Nasıl oynanır (uv run python scripts/run.py)
