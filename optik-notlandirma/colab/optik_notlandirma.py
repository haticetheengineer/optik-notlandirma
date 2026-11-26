import pandas as pd
import re
import io
from google.colab import files


# ============================================================
# 0. OPTİK FORM ŞABLONU (Kapadokya Üniversitesi optik formu)
# ============================================================
# Sütun numaraları 1'den başlar, bitiş dahildir.
# Farklı bir optik form kullanılırsa sadece burayı değiştirin.
SABLON = {
    "ad_bas": 1,   "ad_bit": 20,    # Soyadı Adı
    "tc_bas": 21,  "tc_bit": 31,    # TC Kimlik No (boş olabilir)
    "no_bas": 32,  "no_bit": 39,    # Öğrenci No
    "kit_bas": 40, "kit_bit": 40,   # Kitapçık türü (A-D)
    "tel_bas": 41, "tel_bit": 50,   # Alan kodu + telefon (10 hane)
    "cvp_bas": 51,                  # Cevaplar (120 soru → 51-170)
}


# ============================================================
# 1. CEVAP ANAHTARI VE SORU PUANLARI
# ============================================================

def cevap_anahtari_al():
    """Cevap anahtarını kullanıcıdan al."""
    anahtar = input("📝 Cevap anahtarını girin (örn: ABCDABCD): ").strip().upper().replace(" ", "")
    if not anahtar:
        raise ValueError("❌ Cevap anahtarı boş olamaz!")
    print(f"✅ Cevap anahtarı alındı: {anahtar} ({len(anahtar)} soru)")
    return anahtar


def _puan_listesi_coz(metin):
    """'5,5,10' veya kısaltma '2*20, 6*10' biçimini puan listesine çevirir."""
    puanlar = []
    for parca in metin.replace(";", ",").split(","):
        parca = parca.strip().replace(" ", "")
        if not parca:
            continue
        if "*" in parca:                      # 2*20 → 20 tane 2 puanlık soru
            deger, adet = parca.split("*", 1)
            puanlar.extend([float(deger.replace(",", "."))] * int(adet))
        else:
            puanlar.append(float(parca))
    return puanlar


def soru_puanlari_al(soru_sayisi):
    """Sorular eşit puanlı mı, değilse her sorunun puanını hocadan al."""
    cevap = input("\n⚖️  Sorular eşit puanlı mı? (E/H) [E]: ").strip().upper()
    if cevap in ("", "E", "EVET"):
        puan = 100 / soru_sayisi
        print(f"✅ Eşit puanlama: {soru_sayisi} soru × {round(puan, 4)} puan = 100")
        return [puan] * soru_sayisi

    print("\nHer sorunun puanını sırayla, virgülle ayırarak girin (toplam 100 olmalı).")
    print("   Örnek: 5,5,5,10,10,...")
    print("   Kısaltma: 2*20, 6*10  → ilk 20 soru 2'şer, sonraki 10 soru 6'şar puan")
    while True:
        try:
            puanlar = _puan_listesi_coz(input(f"🔢 {soru_sayisi} sorunun puanları: "))
        except ValueError:
            print("❌ Geçersiz giriş, sadece sayı, virgül ve * kullanın.")
            continue
        if len(puanlar) != soru_sayisi:
            print(f"❌ {len(puanlar)} puan girdiniz, {soru_sayisi} olmalı.")
            continue
        if any(p < 0 for p in puanlar):
            print("❌ Negatif puan olamaz.")
            continue
        toplam = round(sum(puanlar), 2)
        if abs(toplam - 100) > 0.01:
            print(f"❌ Toplam {toplam}; 100 olmalı.")
            continue
        print("✅ Özel puanlama alındı (toplam 100).")
        return puanlar


# ============================================================
# 2. TXT DOSYASINI YÜKLEYİP OKU
# ============================================================

def dosya_yukle():
    """Kullanıcıdan .txt dosyası yüklemesini iste."""
    print("\n📂 Lütfen optik okuyucu .txt dosyanızı yükleyin...")
    uploaded = files.upload()

    for dosya_adi, icerik in uploaded.items():
        if not dosya_adi.lower().endswith(".txt"):
            print(f"⚠️  '{dosya_adi}' bir .txt dosyası değil, atlanıyor.")
            continue
        print(f"✅ Dosya yüklendi: {dosya_adi}")
        for enc in ("utf-8-sig", "cp1254", "latin-1"):
            try:
                return dosya_adi, icerik.decode(enc)
            except UnicodeDecodeError:
                continue

    raise FileNotFoundError("❌ Geçerli bir .txt dosyası yüklenmedi.")


# ============================================================
# 3. SATIR PARSE FONKSİYONU (sabit sütun)
# ============================================================

def _alan(satir, bas, bit):
    """1 tabanlı, bitiş dahil sütun aralığı."""
    return satir[bas - 1:bit]


def cevap_normalize(ham):
    """Boşluk → '0' (boş), A-E aynen, diğer işaretler (*, çift işaret) → '*' (yanlış)."""
    sonuc = []
    for ch in ham.upper():
        if ch in " 0":
            sonuc.append("0")
        elif ch in "ABCDE":
            sonuc.append(ch)
        else:
            sonuc.append("*")
    return "".join(sonuc)


def satir_parse_et(satir, soru_sayisi, sablon=SABLON):
    """Optik okuyucunun sabit sütunlu satırını okur. Dönüş: (veri, hata, uyarilar)"""
    satir = satir.rstrip("\r\n")              # baştaki boşluklar silinmez: cevaplar kaymasın
    if not satir.strip():
        return None, None, []
    s = sablon
    uyarilar = []

    ad_soyad = " ".join(_alan(satir, s["ad_bas"], s["ad_bit"]).split())
    tc       = _alan(satir, s["tc_bas"], s["tc_bit"]).strip()
    ogr_no   = _alan(satir, s["no_bas"], s["no_bit"]).strip().upper()
    kitapcik = _alan(satir, s["kit_bas"], s["kit_bit"]).strip().upper()
    tel_ham  = _alan(satir, s["tel_bas"], s["tel_bit"]).strip()

    if not ad_soyad:
        return None, "Soyadı Adı boş", []
    if not ogr_no:
        return None, f"Öğrenci no boş → {ad_soyad}", []
    if not re.fullmatch(r"C?\d+", ogr_no):
        uyarilar.append(f"Öğrenci no beklenmedik karakter içeriyor ({ogr_no}) → {ad_soyad}")
    if tc and not re.fullmatch(r"\d{11}", tc):
        uyarilar.append(f"TC No 11 haneli değil ({tc}) → {ad_soyad}")

    cep = ""
    if tel_ham:
        if re.fullmatch(r"\d{10}", tel_ham):
            cep = "0" + tel_ham
        else:
            uyarilar.append(f"Telefon eksik/hatalı kodlanmış ({tel_ham}) → {ad_soyad}")

    ham = satir[s["cvp_bas"] - 1:]
    cevaplar = cevap_normalize(ham[:soru_sayisi].ljust(soru_sayisi))
    if ham[soru_sayisi:].strip():
        uyarilar.append(f"Cevap anahtarından sonra işaret var — anahtar kısa olabilir → {ad_soyad}")
    if set(cevaplar) == {"0"}:
        uyarilar.append(f"Tüm sorular boş → {ad_soyad}")

    return {"ad_soyad": ad_soyad, "tc": tc, "ogr_no": ogr_no, "kitapcik": kitapcik,
            "cevaplar": cevaplar, "cep": cep}, None, uyarilar


# ============================================================
# 4. NOTLANDIRMA FONKSİYONU
# ============================================================

def ogrenci_puanla(cevaplar, anahtar, soru_puanlari):
    """
    Doğru cevap → o sorunun puanı
    Yanlış / Boş → 0
    Anahtar X    → iptal soru, herkes o sorunun puanını alır
    """
    cevaplar = cevaplar.ljust(len(anahtar), '0')[:len(anahtar)]
    sonuc = []
    for c, a, puan in zip(cevaplar, anahtar, soru_puanlari):
        if a.upper() == 'X':
            sonuc.append(round(puan, 4))
        elif c not in ('0', ' ', '') and c == a:
            sonuc.append(round(puan, 4))
        else:
            sonuc.append(0)
    return sonuc


# ============================================================
# 5. ANA İŞLEM FONKSİYONU
# ============================================================

def isle(metin, anahtar, soru_puanlari):
    """TXT içeriğini işle, tüm öğrencileri notlandır."""
    satirlar = metin.splitlines()
    print(f"\n📋 Toplam {len(satirlar)} satır işlenecek...\n")

    sonuclar = []
    hata_sayisi = 0

    for i, satir in enumerate(satirlar, start=1):
        veri, hata, uyarilar = satir_parse_et(satir, len(anahtar))
        for u in uyarilar:
            print(f"ℹ️  Satır {i}: {u}")
        if hata:
            hata_sayisi += 1
            print(f"⚠️  Satır {i} atlandı: {hata}")
            continue
        if veri is None:
            continue

        puanlar = ogrenci_puanla(veri["cevaplar"], anahtar, soru_puanlari)

        kayit = {"ogr_no": veri["ogr_no"]}
        for s_no, puan in enumerate(puanlar, start=1):
            kayit[f"S{s_no}"] = puan

        sonuclar.append({
            **kayit,
            "toplam":   round(sum(puanlar), 2),
            "ad_soyad": veri["ad_soyad"],
            "tc":       veri["tc"],
            "cep":      veri["cep"],
            "kitapcik": veri["kitapcik"],
            "cevaplar": veri["cevaplar"],
        })

    print(f"\n✅ {len(sonuclar)} öğrenci başarıyla işlendi.")
    if hata_sayisi:
        print(f"⚠️  {hata_sayisi} satır atlandı.")
    bozuk = sum(1 for r in sonuclar if "�" in r["ad_soyad"])
    if bozuk:
        print(f"⚠️  {bozuk} öğrencinin adında bozuk Türkçe karakter (�) var. "
              f"TXT dosyası yanlış kodlamayla kaydedilmiş olabilir; orijinal dosyayı kullanın.")

    return sonuclar


# ============================================================
# 6. EXCEL OLUŞTURMA FONKSİYONU
# ============================================================

def excel_olustur(sonuclar, anahtar, soru_puanlari):
    soru_sayisi    = len(anahtar)
    esit           = max(soru_puanlari) - min(soru_puanlari) < 1e-6
    soru_kolonlari = [f"S{i}" for i in range(1, soru_sayisi + 1)]
    soru_baslik    = [f"Soru {i} Puanı" for i in range(1, soru_sayisi + 1)]

    # ── Sheet 1: Proliz Not Girişi ─────────────────────────────────────────
    # OgrNo | Soru 1 Puanı | ... | Soru N Puanı  (başlıklı)
    df_proliz = pd.DataFrame(sonuclar)[["ogr_no"] + soru_kolonlari].copy()
    df_proliz.columns = ["Öğrenci Numarası"] + soru_baslik

    # ── Sheet 2: Detaylı Liste ─────────────────────────────────────────────
    df_detay = pd.DataFrame([{
        "Öğrenci Numarası": r["ogr_no"],
        "Soyadı Adı":       r["ad_soyad"],
        "TC No":            r.get("tc", ""),
        "Cep Telefonu":     r.get("cep", ""),
        "Kitapçık":         r.get("kitapcik", ""),
        "Toplam Puan":      r["toplam"],
        **{f"Soru {i} Puanı": r[f"S{i}"] for i in range(1, soru_sayisi + 1)},
    } for r in sonuclar])

    # ── Sheet 3: Özet ──────────────────────────────────────────────────────
    df_ozet = pd.DataFrame([{
        "Öğrenci Numarası": r["ogr_no"],
        "Soyadı Adı":       r["ad_soyad"],
        "TC No":            r.get("tc", ""),
        "Cep Telefonu":     r.get("cep", ""),
        "Toplam Puan":      r["toplam"],
    } for r in sonuclar])

    # ── Sheet 4: Ham TXT ───────────────────────────────────────────────────
    df_ham = pd.DataFrame([{
        "Satır No":         i + 1,
        "Öğrenci Numarası": r["ogr_no"],
        "Soyadı Adı":       r["ad_soyad"],
        "TC No":            r.get("tc", ""),
        "Cep Telefonu":     r.get("cep", ""),
        "Kitapçık":         r.get("kitapcik", ""),
        "Ham Cevaplar":     r.get("cevaplar", ""),
    } for i, r in enumerate(sonuclar)])

    # ── Sheet 5: İşlem Özeti ───────────────────────────────────────────────
    df_islem = pd.DataFrame([
        {"Bilgi": "Soru Sayısı",             "Değer": soru_sayisi},
        {"Bilgi": "Puanlama",                "Değer": "Eşit" if esit else "Soruya göre özel"},
        {"Bilgi": "Soru Başına Puan",        "Değer": round(100 / soru_sayisi, 4) if esit
                                                       else "Soru Puanları sayfasına bakın"},
        {"Bilgi": "İşlenen Öğrenci Sayısı", "Değer": len(sonuclar)},
        {"Bilgi": "Cevap Anahtarı",          "Değer": anahtar},
    ])

    # ── Sheet 6: Soru Puanları ─────────────────────────────────────────────
    df_puan = pd.DataFrame({
        "Soru No":     range(1, soru_sayisi + 1),
        "Doğru Cevap": list(anahtar),
        "Soru Puanı":  [round(p, 4) for p in soru_puanlari],
    })

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_proliz.to_excel(writer, sheet_name="Proliz Not Girişi", index=False)
        df_detay.to_excel(writer,  sheet_name="Detaylı Liste",      index=False)
        df_ozet.to_excel(writer,   sheet_name="Özet",               index=False)
        df_ham.to_excel(writer,    sheet_name="Ham TXT",             index=False)
        df_islem.to_excel(writer,  sheet_name="İşlem Özeti",         index=False)
        df_puan.to_excel(writer,   sheet_name="Soru Puanları",       index=False)
    buf.seek(0)
    return buf


# ============================================================
# 7. MAIN
# ============================================================

def main():
    print("=" * 55)
    print("  OPTİK OKUYUCU OTOMATİK NOTLANDIRMA SİSTEMİ")
    print("=" * 55)

    anahtar          = cevap_anahtari_al()
    soru_puanlari    = soru_puanlari_al(len(anahtar))
    dosya_adi, metin = dosya_yukle()
    sonuclar         = isle(metin, anahtar, soru_puanlari)

    if not sonuclar:
        print("❌ Hiç öğrenci verisi işlenemedi. Dosya formatını kontrol edin.")
        return

    print("\n📊 Excel dosyası oluşturuluyor...")
    excel_buffer = excel_olustur(sonuclar, anahtar, soru_puanlari)

    cikti_adi = dosya_adi.rsplit(".", 1)[0] + ".xlsx"
    with open(cikti_adi, "wb") as f:
        f.write(excel_buffer.read())

    tcli  = sum(1 for r in sonuclar if r.get("tc"))
    cepli = sum(1 for r in sonuclar if r.get("cep"))
    print(f"\n✅ Excel hazır: {cikti_adi}")
    print(f"   • Proliz Not Girişi : {len(sonuclar)} öğrenci, {len(anahtar)} soru")
    print(f"   • Detaylı Liste     : TC + Cep + Kitapçık dahil")
    print(f"   • Özet              : {len(sonuclar)} öğrenci")
    print(f"   • Ham TXT           : ham cevap dizileri")
    print(f"   • İşlem Özeti       : anahtar & puanlama bilgisi")
    print(f"   • Soru Puanları     : her sorunun puanı")
    print(f"   • TC kodlayan       : {tcli} öğrenci")
    print(f"   • Cep tespit edilen : {cepli} öğrenci")
    print("\n⬇️  İndirme başlıyor...")
    files.download(cikti_adi)
    print("🎉 Tamamlandı!")


main()
