SEWANTARA | WAHA outreach untuk kontak yang memberikan izin

File:
- waha_send_optin.py           -> script pengiriman WAHA
- prospek_rental_ps_jember_optin.csv -> data 33 bisnis; seluruh izin awal = BELUM
- .env.waha.example           -> salin ke .env.waha dan isi URL, SESSION, API KEY

Prasyarat:
- Python 3.9+ pada VPS; tidak perlu pip install.
- WAHA session sudah WORKING.
- Setiap penerima harus memberikan izin WhatsApp lebih dulu. Nomor publik tidak berarti consent.
- Catat kolom Izin Kirim WhatsApp = YA; Tanggal Izin (YYYY-MM-DD) = YYYY-MM-DD;
  Sumber Izin = keterangan bukti izin (mis. formulir pendaftaran tester/percakapan inbound).
- Jangan tandai YA tanpa izin. Untuk penolakan, ubah Status Follow-up = Jangan hubungi.
- Periksa fitur produk sebelum mengirim klaim; pesan menyebut fitur yang sedang disiapkan.

Cara menjalankan di VPS:
1. Ekstrak ZIP, cd ke direktori tempat file berada.
2. cp .env.waha.example .env.waha
   Edit URL, nama session, dan API key WAHA. Lindungi file: chmod 600 .env.waha
3. python3 waha_send_optin.py --check
4. python3 waha_send_optin.py --test-number 08XXXXXXXXXX
   (ini hanya preview; gunakan nomor milik Anda)
5. python3 waha_send_optin.py --send --test-number 08XXXXXXXXXX
   (mengirim 1 tes ke nomor Anda sendiri)
6. Isi bukti izin pada CSV untuk kontak yang memang setuju.
7. python3 waha_send_optin.py             # dry-run, tanpa kirim
8. python3 waha_send_optin.py --send --max 5

Catatan:
- Setiap eksekusi --send mengirim paling banyak 5 pesan (default), ke penerima dengan izin.
- Log hasil_kirim_waha.csv mencegah pengiriman ulang untuk respons API sukses.
- API_DITERIMA artinya WAHA menerima request, belum menjamin WhatsApp terkirim/terbaca.
- Kegagalan/timeout bisa ambigu, cek chat manual sebelum ulang.
- Tidak ada trik untuk menghindari blokir: gunakan opt-in dan hormati STOP.
- JANGAN ekspos WAHA endpoint/API key secara publik. Jika di Docker, pastikan URL benar
  dari lingkungan eksekusi. Localhost VPS berbeda dengan localhost container.

Dokumentasi resmi:
https://waha.devlike.pro/docs/how-to/send-messages/
https://waha.devlike.pro/docs/how-to/sessions/
https://waha.devlike.pro/docs/how-to/security/
https://business.whatsapp.com/policy/
