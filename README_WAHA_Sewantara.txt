SEWANTARA | Pengiriman WhatsApp dari CSV melalui WAHA

File:
- waha_send_optin.py           -> script pengiriman WAHA
- prospek_rental_ps_jember_optin.csv -> daftar kontak bisnis
- .env.waha.example           -> salin ke .env.waha dan isi URL, SESSION, API KEY

Prasyarat:
- Python 3.9+ pada VPS; tidak perlu pip install.
- WAHA session sudah WORKING.
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
6. Periksa daftar kontak di CSV. Tandai penolakan dengan Status Follow-up = Jangan hubungi.
7. python3 waha_send_optin.py             # dry-run, tanpa kirim
8. python3 waha_send_optin.py --send --max 5

Catatan:
- Setiap eksekusi --send mencoba paling banyak 5 pengiriman (default) ke kontak yang memenuhi syarat.
- Batch berikutnya melewati nomor yang tercatat sebagai API_DITERIMA atau ERROR_PERIKSA_MANUAL di hasil_kirim_waha.csv.
- API_DITERIMA artinya WAHA menerima request, belum menjamin WhatsApp terkirim/terbaca.
- Kegagalan/timeout bisa ambigu, cek chat manual sebelum ulang.
- Skrip tidak memeriksa kolom Izin Kirim WhatsApp, Sumber Izin, dan Tanggal Izin.
- JANGAN ekspos WAHA endpoint/API key secara publik. Jika di Docker, pastikan URL benar
  dari lingkungan eksekusi. Localhost VPS berbeda dengan localhost container.

Dokumentasi resmi:
https://waha.devlike.pro/docs/how-to/send-messages/
https://waha.devlike.pro/docs/how-to/sessions/
https://waha.devlike.pro/docs/how-to/security/
https://business.whatsapp.com/policy/
