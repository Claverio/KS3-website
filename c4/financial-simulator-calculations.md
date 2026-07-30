# KS3 Financial Simulator — Calculation and Configuration Reference

Dokumen ini menjelaskan kontrak perhitungan yang diimplementasikan oleh
`_product/simulation/engine.py`. Dokumen ini adalah referensi teknis untuk
developer, reviewer keuangan, QA, dan administrator produk. Jika dokumen dan
kode berbeda, kode serta regression test adalah sumber eksekusi aktual dan
perbedaannya harus direkonsiliasi sebelum konfigurasi dipublikasikan.

## 1. Prinsip keselamatan

- Semua kalkulasi backend memakai `Decimal`; perhitungan uang tidak memakai
  floating point biner.
- Nilai uang dibulatkan ke dua desimal dengan `ROUND_HALF_UP` pada setiap
  periode, bukan hanya pada akhir tenor.
- Tenor maksimum sistem adalah 600 bulan.
- Simulator hanya tersedia ketika `is_enabled=true` dan seluruh konfigurasi
  dinyatakan lengkap oleh `ProductSimulation.is_ready`.
- Konfigurasi tidak lengkap gagal secara tertutup: komponen dan aset frontend
  tidak dirender, sedangkan endpoint simulasi mengembalikan HTTP 404.
- Output menyertakan `configuration_version` dan daftar rate/biaya yang benar-
  benar terpakai untuk membantu audit hasil.
- Hasil simulator adalah estimasi. Rate seed di bagian 12 bukan rate resmi.

## 2. Notasi dan pembulatan

| Simbol | Arti |
|---|---|
| `P` | Nominal awal simpanan atau pokok pinjaman |
| `T` | Tenor dalam bulan |
| `B_t` | Saldo/sisa pokok pada periode `t` |
| `C_t` | Setoran rutin pada periode `t` |
| `r_t` | Rate tahunan dalam persen pada periode `t` |
| `i_t` | Rate bulanan desimal, `r_t / 100 / 12` |
| `I_t` | Bunga periode `t` |
| `A_t` | Pembayaran pinjaman periode `t` sebelum/bersama biaya sesuai konteks |
| `F_t` | Biaya periode `t` |
| `X_t` | Pajak periode `t` |
| `R(x)` | Pembulatan uang ke 0,01 dengan `ROUND_HALF_UP` |

Contoh pembulatan: `R(10.000,005) = 10.000,01`.

Frontend menampilkan rupiah tanpa pecahan, tetapi API, tabel sumber, dan seluruh
rekonsiliasi backend tetap menggunakan dua desimal.

## 3. Pemilihan input

### Nominal

Nominal harus memenuhi seluruh syarat berikut:

```text
amount_min <= P <= amount_max
(P - amount_min) mod amount_step = 0
```

Nominal awal boleh nol hanya untuk strategi `savings_recurring`. Ini dibutuhkan
untuk produk yang dimulai tanpa saldo, misalnya proyeksi 12 kali Simpanan Wajib.

### Tenor

- Mode `range`: tenor dibentuk dari `min`, `max`, dan `step`.
- Mode `options`: tenor harus salah satu angka bulan yang ditentukan admin.
- Seluruh tenor harus berupa bilangan bulat positif dan maksimum 600 bulan.

### Setoran rutin

Input ini hanya muncul untuk `savings_recurring` dan mengikuti aturan
minimum/maksimum/step yang sama. Kontribusi dapat diposisikan pada awal atau
akhir periode:

- `beginning`: setoran menerima bunga pada bulan yang sama.
- `end`: setoran mulai menerima bunga pada bulan berikutnya.

## 4. Resolusi rate bunga

### Fixed

Rate tahunan selalu menggunakan `base_annual_rate`.

### Tiered — locked at start

Tier dipilih satu kali memakai nominal awal `P` dan tenor `T`. Batas nominal
bawah inklusif dan batas atas eksklusif:

```text
min_amount <= P < max_amount
```

Jika `max_amount` kosong, tier tidak memiliki batas atas. Jika beberapa tier
overlap, prioritas terbesar dipilih; overlap dengan prioritas sama ditolak.

### Tiered — current balance

Tier dievaluasi ulang setiap bulan menggunakan saldo saat itu. Konfigurasi tanpa
fallback harus memiliki tier batas atas terbuka agar pertumbuhan saldo tidak
keluar dari domain rate.

### Tiered — progressive

Setiap lapisan saldo memakai rate tier-nya sendiri. Effective annual rate yang
ditampilkan untuk saldo `B` adalah:

```text
r_effective = Σ(layer_amount × layer_rate) / B
```

Seluruh saldo harus tercakup oleh tier atau `base_annual_rate` sebagai fallback.
Tier progressive tidak boleh overlap.

## 5. Simpanan

### 5.1 Bunga sederhana — `savings_simple`

Bunga bulanan dihitung dari nominal awal, sehingga tidak berbunga kembali:

```text
I_t = R(P × r_t / 100 / 12)
gross_interest = Σ I_t
```

Saldo jatuh tempo setelah seluruh biaya dan pajak:

```text
maturity_balance = P + Σ I_t - Σ F_t - Σ X_t
```

### 5.2 Bunga majemuk — `savings_compound`

Untuk setiap bulan:

```text
I_t = R(B_before_interest × r_t / 100 / 12)
B_t = B_before_interest + I_t - F_t - X_t
```

Karena bunga dan saldo dibulatkan setiap bulan, hasil dapat berbeda dari formula
pangkat yang hanya membulatkan pada akhir tenor.

### 5.3 Simpanan rutin — `savings_recurring`

Strategi ini memakai pertumbuhan saldo majemuk dan menambahkan `C_t`.

Kontribusi awal periode:

```text
B_interest_base = B_(t-1) + C_t
I_t = R(B_interest_base × r_t / 100 / 12)
B_t = B_interest_base + I_t - F_t - X_t
```

Kontribusi akhir periode:

```text
I_t = R(B_(t-1) × r_t / 100 / 12)
B_t = B_(t-1) + I_t - F_t - X_t + C_t
```

Total setoran adalah `P + Σ C_t`.

## 6. Pinjaman

Seluruh strategi merekonsiliasi pembayaran pokok terakhir agar sisa pokok tepat
`0,00`, termasuk koreksi selisih pembulatan sen.

### 6.1 Bunga flat — `loan_flat`

```text
principal_t = R(P / T), kecuali periode terakhir
interest_t  = R(P × r / 100 / 12)
payment_t   = principal_t + interest_t + scheduled_fee_t + tax_t
```

Rate wajib dikunci dari nominal awal dan tenor.

### 6.2 Pokok tetap / bunga menurun — `loan_declining`

```text
principal_t = R(P / T), kecuali periode terakhir
interest_t  = R(B_(t-1) × r_t / 100 / 12)
payment_t   = principal_t + interest_t + scheduled_fee_t + tax_t
```

Pokok relatif tetap, sedangkan bunga menurun mengikuti sisa pinjaman.

### 6.3 Anuitas — `loan_annuity`

Untuk rate bulanan `i` dan sisa periode `n`:

```text
A = R(B × i × (1 + i)^n / ((1 + i)^n - 1))
interest_t  = R(B_(t-1) × i_t)
principal_t = R(A - interest_t)
```

Jika rate nol, `A = R(B / n)`. Untuk rate yang dievaluasi dari current balance,
angsuran dihitung ulang dari rate dan sisa tenor pada periode tersebut.

### 6.4 Bullet — `loan_bullet`

```text
principal_t = 0, untuk t < T
principal_T = seluruh sisa pokok
interest_t  = R(B_(t-1) × r_t / 100 / 12)
```

## 7. Biaya dan pajak

Setiap rule memiliki kategori, cara hitung, basis, timing, dan batas opsional.

### Cara hitung

```text
fixed:      charge = value
percentage: charge = basis × value / 100
charge = min(max(charge, minimum_amount), maximum_amount)
charge = R(charge)
```

Basis yang tersedia:

- nominal awal;
- saldo awal periode;
- bunga periode;
- pembayaran periode;
- total bunga, hanya saat jatuh tempo.

Timing yang tersedia:

- `upfront`: dihitung sebelum jadwal periodik;
- `per_period`: dihitung setiap bulan;
- `maturity`: dihitung pada periode terakhir.

Untuk simpanan, biaya upfront mengurangi saldo pembuka satu kali dan tetap
ditampilkan pada baris pertama. Untuk pinjaman, biaya upfront mengurangi dana
bersih diterima dan tidak ditambahkan kembali ke angsuran. Total biaya upfront
pinjaman tidak boleh melebihi nominal pinjaman.

## 8. Ringkasan dan rekonsiliasi

### Simpanan

```text
total_contributions = P + Σ C_t
gross_interest      = Σ I_t
total_fees          = Σ F_t
total_tax           = Σ X_t
net_interest        = gross_interest - total_tax
maturity_balance    = closing_balance periode terakhir
```

Invariant utama:

```text
maturity_balance = total_contributions + gross_interest - total_fees - total_tax
```

### Pinjaman

```text
net_disbursed           = P - upfront_fees - upfront_tax
total_principal         = Σ principal_t = P
total_interest          = Σ interest_t
total_scheduled_payment = Σ payment_t
total_cost              = total_interest + total_fees + total_tax
```

Kurva `Total pembayaran` memakai `Σ payment_t`, sehingga biaya yang sudah
dipotong dari pencairan tidak dihitung kembali sebagai pembayaran angsuran.

## 9. Breakdown adaptif

Jadwal selalu dihitung bulanan terlebih dahulu. Ringkasan tampilan kemudian
menggabungkan beberapa baris tanpa mengubah total finansial:

- saldo awal: saldo baris pertama dalam kelompok;
- pokok, bunga, setoran, biaya, pajak, pembayaran: dijumlahkan;
- saldo akhir dan nilai kumulatif: nilai baris terakhir;
- rate: minimum dan maksimum rate dalam kelompok.

### Auto compact

Memilih interval pertama dari `1, 3, 6, 12, 24, 60` bulan yang menghasilkan
maksimal 12 baris.

| Tenor | Interval | Baris |
|---:|---:|---:|
| 12 bulan | 1 bulan | 12 |
| 24 bulan | 3 bulan | 8 |
| 36 bulan | 3 bulan | 12 |
| 60 bulan | 6 bulan | 10 |
| 120 bulan | 12 bulan | 10 |
| 600 bulan | 60 bulan | 10 |

### Auto detailed

Algoritma sama tetapi target maksimal 20 baris. Contoh: 60 bulan memakai
interval 3 bulan sehingga menghasilkan 20 baris.

### Fixed dan custom

- `fixed`: admin memilih interval tetap.
- `custom`: interval dipilih dari band tenor yang cocok; prioritas terbesar
  menang. Seluruh pilihan tenor harus tercakup dan top priority tidak boleh
  ambigu.

Grafik memiliki sampling terpisah:

```text
chart_interval = max(1, ceil(T / 60))
```

Karena itu grafik maksimal 60 titik, tetapi total pada grafik tetap berasal dari
jadwal bulanan yang sama.

## 10. Kontrak endpoint

```text
GET /product/{slug}/simulation/?amount=...&tenor_months=...&recurring_amount=...
```

- Produk harus published dan kategorinya aktif.
- Simulator disabled/tidak lengkap: HTTP 404.
- Input anggota tidak valid: HTTP 400 dengan error per field.
- Berhasil: metadata, input ternormalisasi, applied rules, summary, breakdown,
  dan chart.
- Endpoint read-only; method selain GET ditolak.

## 11. Contoh hitung terverifikasi

### Simpanan Berjangka seed

Nominal Rp10.000.000, tenor 12 bulan, rate locked 5,25% p.a., bunga sederhana,
pajak hasil seed 20% saat jatuh tempo:

```text
bunga bruto = 10.000.000 × 5,25% × 12/12 = 525.000
pajak        = 525.000 × 20%             = 105.000
saldo akhir  = 10.000.000 + 525.000 - 105.000
             = 10.420.000
```

### Simpanan Wajib seed

Saldo awal Rp0, setoran Rp100.000 pada awal bulan, tenor 12 bulan, rate 0%:

```text
total setoran = 12 × 100.000 = 1.200.000
bunga         = 0
saldo akhir   = 1.200.000
```

### Pinjaman flat

Nominal Rp12.000.000, tenor 12 bulan, rate 12% p.a., tanpa biaya:

```text
pokok bulanan = 1.000.000
bunga bulanan = 120.000
angsuran      = 1.120.000
total bayar   = 13.440.000
```

### Pinjaman Usaha Produktif seed

Nominal Rp250.000.000, tenor 36 bulan, anuitas dengan rate progresif tiga
lapis. Rate periode dihitung sebagai rata-rata tertimbang lapisan sisa pokok
yang masih terpakai:

```text
Lapisan Rp0–<Rp50 juta       = 10% p.a.
Lapisan Rp50–<Rp150 juta     = 11,5% p.a.
Lapisan mulai Rp150 juta     = 13% p.a.

Rate efektif awal
= (50 juta × 10% + 100 juta × 11,5% + 100 juta × 13%) / 250 juta
= 11,8% p.a.
```

Biaya seed default:

```text
provisi 1%, capped Rp2.000.000 = Rp2.000.000
administrasi tetap             = Rp  100.000
asuransi 0,5%                  = Rp1.250.000
potongan awal                  = Rp3.350.000
dana bersih diterima           = Rp246.650.000
biaya layanan 36 × Rp15.000    = Rp  540.000
total biaya                    = Rp3.890.000
```

Hasil engine untuk preset default:

```text
total pokok             = Rp250.000.000
total bunga             = Rp45.766.750,46
total pembayaran jadwal = Rp296.306.750,46
rentang angsuran         = Rp8.187.119,55–Rp8.294.716,72
sisa pokok akhir         = Rp0
breakdown                = per triwulan, 12 baris
```

Rentang angsuran muncul karena rate progresif dievaluasi ulang dari sisa pokok
dan angsuran anuitas dihitung kembali untuk sisa periode.

## 12. Seed produk KS3 saat ini

Seed dapat dijalankan tanpa mengubah konten/gambar produk:

```bash
python manage.py seed_product_simulators --strict
```

`seed_product_showcase` juga menjalankan seed simulator setelah membuat tujuh
produk. Seed idempotent dan mengganti child rate/fee/breakdown untuk ketujuh slug
yang dikenal.

| Produk | Strategi | Asumsi seed | Status publik |
|---|---|---|---|
| Simpanan Wajib | Setoran rutin | Rp100.000/bulan, 0% | Aktif |
| Simpanan Sukarela | Setoran rutin fleksibel | 3% p.a. | Aktif |
| Simpanan Berjangka | Bunga sederhana, tier nominal+tenor | 3,5%–5,25% p.a.; pajak ilustratif 20% | Aktif |
| Simpanan Pokok | Setoran satu kali | Rp100.000, 0% | Nonaktif karena tidak membutuhkan proyeksi pertumbuhan |
| Simpanan Lain | Tabungan tujuan rutin | 3,25% p.a. | Aktif |
| Pinjaman Reguler | Bunga flat | 12% p.a.; tanpa biaya | Aktif |
| Pinjaman Usaha Produktif | Anuitas, tier progresif | 10%–13% p.a.; provisi, administrasi, asuransi, dan biaya layanan ilustratif | Aktif |

Semua asumsi seed ditandai `assumption_status=illustrative` dan memiliki
disclaimer publik. Administrator wajib mengganti rate, nominal, pajak, serta
ketentuan sesuai dokumen produk resmi sebelum menjadikannya dasar komunikasi
komersial.

## 13. Checklist review produk keuangan

Sebelum mengaktifkan simulator:

1. Cocokkan strategi dengan akad/ketentuan produk.
2. Verifikasi apakah rate flat, efektif, anuitas, current balance, atau
   progressive.
3. Verifikasi batas tier: bawah inklusif, atas eksklusif.
4. Pastikan seluruh kombinasi nominal dan tenor tercakup.
5. Konfirmasi waktu setoran rutin: awal atau akhir periode.
6. Konfirmasi timing dan basis biaya/pajak.
7. Rekonsiliasi satu contoh manual terhadap summary dan breakdown API.
8. Uji nilai minimum, batas tier, maksimum, tenor terpendek, dan terpanjang.
9. Pastikan disclaimer tidak kosong dan tidak menjanjikan hasil final.
10. Catat `configuration_version` yang telah disetujui reviewer.
