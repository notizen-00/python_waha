#!/usr/bin/env python3
"""Sewantara: WAHA WhatsApp outreach from CSV, standard-library only.

Default: dry-run. Bulk sending skips opted-out contacts and numbers with a logged bulk send attempt. Nothing is sent unless --send is provided.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = ROOT / 'prospek_rental_ps_jember_optin.csv'
DEFAULT_LOG = ROOT / 'hasil_kirim_waha.csv'
LOG_FIELDS = ['waktu', 'nama_bisnis', 'nomor_62', 'hasil', 'detail']


def read_env_file(path: Path):
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in {'WAHA_URL', 'WAHA_SESSION', 'WAHA_API_KEY'}:
            os.environ.setdefault(k, v)


def normalize_phone(value):
    raw = re.sub(r'[^0-9+]', '', str(value or ''))
    if raw.startswith('+'):
        raw = raw[1:]
    if raw.startswith('0'):
        raw = '62' + raw[1:]
    elif raw.startswith('8'):
        raw = '62' + raw
    if not raw.startswith('62') or not raw.isdigit() or not 10 <= len(raw) <= 16:
        return None
    return raw


def message():
    return """Halo, selamat siang Kak! 👋

Perkenalkan, saya dari *Sewantara*, platform digital yang sedang kami kembangkan untuk membantu pemilik usaha rental PlayStation mengelola bisnis dengan lebih mudah dan modern.

Saat ini, kami sedang mencari beberapa *mitra rental PS di wilayah Jember* yang bersedia menjadi _early tester_ sistem kami secara *GRATIS selama 1 bulan*, tanpa kewajiban berlangganan setelah masa uji coba.

🎮 *Apa saja keuntungan yang bisa Kakak dapatkan?*

✅ *Booking Online 24 Jam* — Pelanggan nantinya bisa melihat ketersediaan dan melakukan booking PS secara online tanpa harus datang langsung.

✅ *Manajemen Rental* — Membantu mencatat penyewaan, durasi bermain, dan transaksi pelanggan.

✅ *Pengelolaan Unit PS* — Memantau unit yang tersedia, sedang digunakan, maupun sudah dibooking.

✅ *Laporan Bisnis* — Melihat pemasukan dan aktivitas rental melalui dashboard.

✅ *Peluang Masuk Marketplace Sewantara* — Ke depannya, rental Kakak berkesempatan tampil di marketplace rental PlayStation wilayah Jember agar lebih mudah ditemukan calon pelanggan.

Karena platform ini masih dalam tahap pengembangan, kami juga ingin mendengar masukan langsung dari pemilik rental agar fitur yang kami bangun benar-benar sesuai kebutuhan di lapangan.

*Apakah Kakak berkenan menjadi salah satu mitra tester awal Sewantara secara gratis?* 😊

Jika berkenan, kami dengan senang hati akan menjelaskan sistemnya lebih lanjut.

Terima kasih atas waktunya, Kak! 🙏

*Tim Sewantara*
🌐 https://sewantara.id"""


def request_json(base_url, api_key, path, method='GET', payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Accept': 'application/json'}
    if api_key:
        headers['X-Api-Key'] = api_key
    if data is not None:
        headers['Content-Type'] = 'application/json'
    request = Request(base_url.rstrip('/') + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read(32768).decode('utf-8', errors='replace')
            try:
                output = json.loads(body) if body else {}
            except json.JSONDecodeError:
                output = {'raw': body[:300]}
            return response.status, output
    except HTTPError as ex:
        body = ex.read(2048).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {ex.code}: {body[:250]}') from ex
    except (URLError, TimeoutError) as ex:
        raise RuntimeError(f'Koneksi WAHA gagal: {ex}') from ex


def check_session(base_url, api_key, session):
    status, payload = request_json(base_url, api_key, '/api/sessions/' + quote(session, safe=''))
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f'Respons sesi tidak valid: HTTP {status}')
    name, state = payload.get('name'), payload.get('status')
    print(f'WAHA session: {name!r} | status: {state!r}')
    if state != 'WORKING':
        raise RuntimeError('Session WAHA belum WORKING; periksa pairing / koneksi sebelum kirim')


def read_contacts(path):
    if not path.exists():
        raise RuntimeError(f'CSV tidak ditemukan: {path}')
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def read_attempted(path):
    if not path.exists():
        return set()
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        rows = csv.DictReader(f)
        return {
            row['nomor_62'] for row in rows
            if row.get('nomor_62') and row.get('hasil') in {'API_DITERIMA', 'ERROR_PERIKSA_MANUAL'}
        }


def save_result(path, name, phone, result, detail):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open('a', newline='', encoding='utf-8-sig' if not exists else 'utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({
            'waktu': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'nama_bisnis': name,
            'nomor_62': phone,
            'hasil': result,
            'detail': detail[:400],
        })


def has_opted_out(row):
    current_status = str(row.get('Status Follow-up', '')).strip().casefold()
    return any(flag in current_status for flag in ('jangan hubungi', 'stop', 'menolak', 'tolak', 'opt-out', 'unsubscribe'))


def do_send(base_url, api_key, session, phone, text):
    return request_json(base_url, api_key, '/api/sendText', 'POST', {
        'session': session,
        'chatId': phone + '@c.us',
        'text': text,
    })


def main():
    read_env_file(ROOT / '.env.waha')
    parser = argparse.ArgumentParser(description='Sewantara WAHA CSV outreach; default dry-run')
    parser.add_argument('--csv', type=Path, default=DEFAULT_CSV)
    parser.add_argument('--results', type=Path, default=DEFAULT_LOG)
    parser.add_argument('--check', action='store_true', help='Periksa status session saja')
    parser.add_argument('--test-number', metavar='YOUR_OWN_NUMBER', help='Tes hanya ke nomor WhatsApp milik Anda')
    parser.add_argument('--send', action='store_true', help='Benar-benar kirim; tanpa ini hanya simulasi')
    parser.add_argument('--max', type=int, default=5, help='Maksimum pesan sekali eksekusi (1-20, default: 5)')
    parser.add_argument('--delay', type=int, default=12, help='Jeda antar pesan dalam detik (min: 10)')
    args = parser.parse_args()

    if args.max < 1 or args.max > 20:
        parser.error('--max harus 1..20')
    if args.delay < 10:
        parser.error('--delay minimal 10 detik; tidak menjamin bebas blokir')

    base_url = os.getenv('WAHA_URL', 'http://127.0.0.1:3000').strip()
    api_key = os.getenv('WAHA_API_KEY', '').strip()
    session = os.getenv('WAHA_SESSION', 'default').strip()
    if not base_url.startswith(('http://', 'https://')):
        parser.error('WAHA_URL wajib diawali http:// atau https://')
    if args.send or args.check:
        try:
            check_session(base_url, api_key, session)
        except RuntimeError as ex:
            print(f'ERROR: {ex}', file=sys.stderr)
            return 1
    if args.check:
        return 0

    if args.test_number:
        phone = normalize_phone(args.test_number)
        if not phone:
            parser.error('Nomor tes tidak valid; gunakan format 08... atau 628...')
        text = message()
        if not args.send:
            print(f'[DRY-RUN TES] {phone}@c.us\n\n{text}')
            return 0
        print(f'Mengirim tes ke nomor milik Anda: {phone}')
        try:
            status, payload = do_send(base_url, api_key, session, phone, text)
            if status in (200, 201, 202):
                save_result(args.results, 'TES INTERNAL', phone, 'TES_API_DITERIMA', str(payload)[:250])
                print('API WAHA menerima permintaan tes. Periksa WhatsApp penerima untuk konfirmasi terkirim.')
                return 0
            print(f'HTTP tidak diharapkan: {status}: {payload}', file=sys.stderr)
            return 1
        except RuntimeError as ex:
            print(f'ERROR: {ex}', file=sys.stderr)
            return 1

    try:
        rows = read_contacts(args.csv)
    except RuntimeError as ex:
        print(f'ERROR: {ex}', file=sys.stderr)
        return 1

    attempted = read_attempted(args.results)
    queued = []
    seen = set()
    invalid = 0
    for row in rows:
        if has_opted_out(row):
            continue
        phone = normalize_phone(row.get('Nomor Publik (teks)', ''))
        if phone is None:
            invalid += 1
            continue
        if phone in seen or phone in attempted:
            continue
        seen.add(phone)
        queued.append((phone, row.get('Nama Bisnis', '').strip()))
    print(f'Total kontak CSV: {len(rows)} | Siap dikirim: {len(queued)} | Nomor invalid: {invalid}')
    if not queued:
        print('Tidak ada kontak yang siap dikirim.')
        return 0

    batch = queued[:args.max]
    if not args.send:
        print('DRY-RUN. Daftar calon penerima:')
        for phone, name in batch:
            print(f'  {phone}: {name}')
        print('\nContoh isi pesan:\n' + message())
        print('\nTambahkan --send untuk mengirim pesan ke batch ini.')
        return 0

    n = 0
    for idx, (phone, name) in enumerate(batch, 1):
        try:
            status, payload = do_send(base_url, api_key, session, phone, message())
            if status not in (200, 201, 202):
                raise RuntimeError(f'HTTP {status}: {str(payload)[:250]}')
            save_result(args.results, name, phone, 'API_DITERIMA', str(payload)[:250])
            n += 1
            print(f'[{idx}/{len(batch)}] API diterima: {name} ({phone})')
        except RuntimeError as ex:
            save_result(args.results, name, phone, 'ERROR_PERIKSA_MANUAL', str(ex))
            print(f'[{idx}/{len(batch)}] ERROR: {name} ({phone}) - {ex}', file=sys.stderr)
            print('Nomor ini dilewati pada batch berikutnya. Periksa chat dan log WAHA.')
        if idx < len(batch):
            time.sleep(args.delay)
    print(f'API menerima {n}/{len(batch)} permintaan. BUKAN bukti pesan telah diterima/dibaca.')
    print(f'Log: {args.results}')
    return 0 if n == len(batch) else 2


if __name__ == '__main__':
    sys.exit(main())
