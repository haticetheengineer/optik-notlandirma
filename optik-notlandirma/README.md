# Optik Notlandırma Sistemi

Kapadokya Üniversitesi optik okuyucusunun ürettiği TXT dosyalarını notlandırıp
Excel (Proliz formatı dahil 6 sayfa) ve PDF analiz raporu üreten Streamlit uygulaması.

Geliştiren: Öğr. Gör. Hatice Tekiş

## Klasör yapısı

```
app.py                       Streamlit uygulaması (ana dosya)
requirements.txt             Python bağımlılıkları
fonts/                       PDF için DejaVu fontları (Türkçe karakter desteği)
.streamlit/secrets.toml.example  İsteğe bağlı giriş bilgisi ayarı
colab/optik_notlandirma.py   Google Colab sürümü (sunucuya yüklenmez)
```

## Çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Community Cloud'da "Main file path" olarak `app.py` seçin.

## Giriş

Kullanıcı adı: `tekisjet` — şifre kodda yalnızca SHA-256 özeti olarak tutulur.
Değiştirmek için `.streamlit/secrets.toml.example` dosyasına bakın.

## TXT formatı (sabit sütun)

| Sütun   | Alan                         |
|---------|------------------------------|
| 1–20    | Soyadı Adı                   |
| 21–31   | TC Kimlik No (boş olabilir)  |
| 32–39   | Öğrenci No                   |
| 40      | Kitapçık türü                |
| 41–50   | Alan kodu + telefon          |
| 51–170  | Cevaplar (120 soru)          |

- Boş bırakılan soru → boş, çift/geçersiz işaret → yanlış
- Anahtarda `X` → iptal soru, herkes o sorunun puanını alır
- Farklı bir optik form için sütunlar uygulamadaki "Optik form şablonu" bölümünden
  (Colab sürümünde dosya başındaki `SABLON`) değiştirilebilir.

## Puanlama

- **Eşit dağıt:** 100 puan sorulara eşit bölünür.
- **Soru başına puan gir:** her sorunun puanı tek tek girilir (toplam 100 olmalı).
  Colab sürümünde `2*20, 6*10` kısaltması kullanılabilir.

## Not

Öğrenci TXT dosyaları kişisel veri (TC, telefon) içerir; `.gitignore` bunları
repoya eklemez. Repoyu herkese açık yapmadan önce bunu kontrol edin.
