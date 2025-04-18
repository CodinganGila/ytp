import subprocess
import sys
import os
import time
import tempfile
from threading import Thread
from termcolor import colored
import pyfiglet
from tabulate import tabulate
import json

# Fungsi dari ytp.py


def create_ipc_socket():
    socket_dir = os.path.expanduser("~/.mpv_sockets")
    os.makedirs(socket_dir, exist_ok=True)
    return tempfile.mktemp(prefix="mpvsocket_", dir=socket_dir)


def garis(teks="=", panjang=60):
    return teks * panjang


def header():
    os.system("clear")
    print(colored(garis(), "cyan"))
    print(colored(pyfiglet.figlet_format("YTube Fast", font="slant"), "magenta"))
    print(colored(garis(), "cyan"))
    print(colored("Masukkan jenis input:", "yellow", attrs=["bold"]))
    print(colored("1. Judul atau Link YouTube", "green"))
    print(colored("2. Playlist YouTube", "green"))
    print(colored("3. Download Audio YouTube", "green"))
    print(colored("4. Putar dengan Spotify", "green"))  # Opsi baru
    print(colored("0. Keluar", "red"))
    print(colored(garis("-"), "cyan"))


def tampil_kontrol():
    print(colored(garis(), "cyan"))
    print(colored(" Kontrol Pemutaran MPV ".center(
        60, "="), "green", attrs=["bold"]))
    print(colored("""
     ► [←]  Seek -5 detik        [→]  Seek +5 detik
     ► [↑]  Seek +1 menit        [↓]  Seek -1 menit
     
     ► [0]  Volume +2%           [9]  Volume -2%
     
     ► [<] Previous              [>]  Next
     ► [SPACE] Play / Pause      [q]  Berhenti & Keluar
    """, "yellow"))
    print(colored(garis(), "cyan"))


def hapus_socket(ipc_socket):
    if os.path.exists(ipc_socket):
        os.remove(ipc_socket)


def play_mpv(url, title, duration, uploader):
    ipc_socket = create_ipc_socket()
    cmd = [
        "mpv", "--no-video",
        f"--input-ipc-server={ipc_socket}",
        "--term-playing-msg=",
        "--force-window=no",
        "--ytdl-format=bestaudio",
        f"--ytdl-raw-options=cookies=cookies.txt",
        url
    ]
    process = subprocess.Popen(cmd)
    for _ in range(20):
        if os.path.exists(ipc_socket):
            break
        time.sleep(0.2)
    else:
        print(colored("Gagal membuat socket IPC", "red"))
        return
    Thread(target=monitor_status, args=(ipc_socket,), daemon=True).start()
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n" + colored("Terhenti. Keluar.", "red"))
        process.terminate()
    hapus_socket(ipc_socket)


def monitor_status(ipc_socket):
    while True:
        try:
            for prop in ["time-pos", "duration", "media-title"]:
                subprocess.run(["socat", "-", f"UNIX-CONNECT:{ipc_socket}"],
                               input=json.dumps(
                                   {"command": ["observe_property", 1, prop]}) + "\n",
                               text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
        except Exception:
            time.sleep(0.2)
    while os.path.exists(ipc_socket):
        try:
            res = subprocess.run(["socat", "-", f"UNIX-CONNECT:{ipc_socket}"],
                                 input='{"command": ["get_property", "time-pos"]}\n{"command": ["get_property", "duration"]}\n',
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            lines = res.stdout.strip().splitlines()
            times = []
            for line in lines:
                if '"data"' in line:
                    try:
                        val = float(line.split('"data":')[1].split("}")[0])
                        times.append(val)
                    except:
                        pass
            if len(times) == 2:
                t, d = times
                percent = int((t / d) * 100)
                mins, secs = divmod(int(t), 60)
                dur_m, dur_s = divmod(int(d), 60)
                print(
                    f"{mins:02}:{secs:02} / {dur_m:02}:{dur_s:02} ({percent}%)", end="\r")
            time.sleep(1)
        except Exception:
            break


def get_metadata(url):
    result = subprocess.run(
        ["yt-dlp", "--cookies", "cookies.txt", "--print",
            "%(title)s\n%(duration_string)s\n%(uploader)s", url],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    lines = result.stdout.strip().split("\n")
    if len(lines) >= 3:
        return lines[0], lines[1], lines[2]
    return url, "??:??", "Unknown"


def ulangi_pemutaran():
    print(colored("\nPilih aksi:", "cyan", attrs=["bold"]))
    print(colored("1. Ulangi pemutaran", "green"))
    print(colored("2. Kembali ke awal", "green"))
    print(colored("0. Keluar", "red"))
    try:
        return input(colored("Pilih aksi [0-2]: ", "cyan", attrs=["bold"])).strip().lower()
    except KeyboardInterrupt:
        print("\n" + colored("Terhenti. Keluar.", "red"))
        sys.exit(0)


def pilih_dengan_fzf(hasil):
    try:
        daftar = "\n".join(
            [f"{title} | {dur} | {url}" for title, dur, url in hasil])
        fzf = subprocess.run(["fzf", "--prompt=◉ Pilih: "],
                             input=daftar, stdout=subprocess.PIPE, text=True)
        if fzf.returncode != 0 or not fzf.stdout.strip():
            return None
        line = fzf.stdout.strip()
        parts = line.split(" | ")
        if len(parts) == 3:
            return parts[2]
    except Exception as e:
        print(colored(f"Gagal pakai fzf: {e}", "red"))
    return None


def download_audio(url, gunakan_fzf=False):
    try:
        if "playlist" in url:
            print(colored("\nPilih video untuk diunduh:",
                  "yellow", attrs=["bold"]))
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print",
                    "%(title)s|%(duration_string)s|https://www.youtube.com/watch?v=%(id)s", url],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            lines = result.stdout.strip().splitlines()
            hasil = []
            for line in lines:
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) == 3:
                        title, dur, link = [p.strip() for p in parts]
                        hasil.append((title, dur, link))
            if gunakan_fzf:
                url_video = pilih_dengan_fzf(hasil)
                if not url_video:
                    print(
                        colored("Tidak ada video yang dipilih, kembali ke menu.", "red"))
                    return
            else:
                url_video = hasil[0][2] if hasil else None
                if not url_video:
                    print(
                        colored("Playlist kosong atau tidak ada video yang dapat dipilih.", "red"))
                    return
            print(colored(
                "\nMengunduh audio (otomatis kualitas terbaik)...", "blue", attrs=["bold"]))
            cmd = ["yt-dlp", "-x", "--embed-thumbnail", "--add-metadata",
                   "--output", "%(title)s.%(ext)s", url_video]
            try:
                subprocess.run(cmd, check=True)
                print(colored("✓ Unduhan selesai!", "green", attrs=["bold"]))
            except subprocess.CalledProcessError:
                print(colored("✗ Gagal mengunduh audio.",
                      "red", attrs=["bold"]))
        else:
            print(colored(
                "\nMengunduh audio (otomatis kualitas terbaik)...", "blue", attrs=["bold"]))
            cmd = ["yt-dlp", "-x", "--embed-thumbnail",
                   "--add-metadata", "--output", "%(title)s.%(ext)s", url]
            try:
                subprocess.run(cmd, check=True)
                print(colored("✓ Unduhan selesai!", "green", attrs=["bold"]))
            except subprocess.CalledProcessError:
                print(colored("✗ Gagal mengunduh audio.",
                      "red", attrs=["bold"]))
    except KeyboardInterrupt:
        print("\n" + colored("Unduhan dihentikan.", "red"))

# Fungsi dari script Spotify


def play_mp3(mp3):
    print(colored(f"\nMemutar {mp3}...\n", "green"))
    subprocess.run(["mpv", "--no-video", mp3])


def get_duration(file):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        duration = float(result.stdout.strip())
        mins, secs = divmod(int(duration), 60)
        return f"{mins:02}:{secs:02}"
    except:
        return "N/A"


def wait_for_downloads(expected_count, timeout=180):
    print(colored(f"\n{garis('=', 60)}", "cyan"))
    print(colored(" Menunggu Unduhan Selesai ".center(
        60, " "), "yellow", attrs=["bold"]))
    print(
        colored(f"Menunggu {expected_count} file mp3 selesai diunduh...", "cyan"))
    print(colored(garis('=', 60), "cyan"))

    elapsed = 0
    while elapsed < timeout:
        mp3_files = sorted([f for f in os.listdir() if f.endswith(".mp3")])
        if len(mp3_files) >= expected_count:
            print(colored("\n🎵 Daftar Lagu yang Ditemukan 🎵",
                  "magenta", attrs=["bold"]))
            print(colored(garis('-', 60), "cyan"))
            table = [[
                colored(f"{i+1}", "green", attrs=["bold"]),
                colored(f.replace('.mp3', ''), "white"),
                colored(get_duration(f), "cyan")
            ] for i, f in enumerate(mp3_files)]
            print(tabulate(table, headers=[
                colored("#", "yellow", attrs=["bold"]),
                colored("Nama Lagu", "yellow", attrs=["bold"]),
                colored("Durasi", "yellow", attrs=["bold"])
            ], tablefmt="rounded_grid", stralign="left"))
            print(colored(garis('-', 60), "cyan"))
            return mp3_files
        time.sleep(2)
        elapsed += 2

    mp3_files = sorted([f for f in os.listdir() if f.endswith(".mp3")])
    if mp3_files:
        print(colored("\n🎵 Daftar Lagu yang Ditemukan (Waktu Habis) 🎵",
              "magenta", attrs=["bold"]))
        print(colored(garis('-', 60), "cyan"))
        table = [[
            colored(f"{i+1}", "green", attrs=["bold"]),
            colored(f.replace('.mp3', ''), "white"),
            colored(get_duration(f), "cyan")
        ] for i, f in enumerate(mp3_files)]
        print(tabulate(table, headers=[
            colored("#", "yellow", attrs=["bold"]),
            colored("Nama Lagu", "yellow", attrs=["bold"]),
            colored("Durasi", "yellow", attrs=["bold"])
        ], tablefmt="rounded_grid", stralign="left"))
        print(colored(garis('-', 60), "cyan"))
    else:
        print(colored("Tidak ada file mp3 yang ditemukan.", "red"))
    return mp3_files


def estimate_song_count(link):
    return 4  # Estimasi sederhana, bisa diperbaiki jika ada logika lebih spesifik


def play_spotify_link(link):
    try:
        print(colored("\nMengunduh lagu dari Spotify...\n",
              "cyan", attrs=["bold"]))
        subprocess.Popen(f"spotdl {link}", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(colored("Pengecekan file mp3...", "yellow"))
        expected_count = estimate_song_count(link)
        mp3_files = wait_for_downloads(expected_count)
        if not mp3_files:
            print(colored("Tidak ada file mp3 yang ditemukan.", "red"))
            return None, []
        return None, mp3_files
    except subprocess.CalledProcessError as e:
        print(colored(f"Terjadi kesalahan: {e.stderr.decode()}", "red"))
        return None, []


def show_menu_spotify():
    print(colored("\nMenu setelah lagu diputar:", "blue", attrs=["bold"]))
    print(colored("1. Putar semua lagu", "green"))
    print(colored("2. Masukkan link Spotify baru", "green"))
    print(colored("3. Simpan lagu dan keluar", "green"))
    print(colored("4. Kembali ke awal", "green"))
    print(colored("0. Keluar", "red"))
    try:
        return input(colored("Pilih aksi [0-4]: ", "cyan", attrs=["bold"])).strip().lower()
    except KeyboardInterrupt:
        print("\n" + colored("Terhenti. Keluar.", "red"))
        sys.exit(0)


def main():
    last_played = None
    downloaded_files = []

    while True:
        try:
            header()
            opsi = input(
                colored("Pilih opsi [0-4]: ", "cyan", attrs=["bold"])).strip()

            if opsi == "0":
                print(colored("Keluar.", "red"))
                sys.exit(0)

            elif opsi == "1":
                try:
                    print(colored("\nPilih cara pemutaran:",
                          "yellow", attrs=["bold"]))
                    print(colored("1. Putar dengan fzf", "green"))
                    print(colored("2. Putar langsung tanpa fzf", "green"))
                    print(colored("3. Putar langsung dari link YouTube", "green"))
                    print(colored("0. Kembali ke awal", "red"))
                    pilihan = input(
                        colored("Pilih opsi [0-3]: ", "cyan", attrs=["bold"])).strip()

                    if pilihan == "0":
                        continue
                    elif pilihan == "1":
                        query = input(colored("Masukkan judul: ",
                                      "green", attrs=["bold"])).strip()
                        print(colored("Mencari...", "blue"))
                        result = subprocess.run(
                            ["yt-dlp", f"ytsearch10:{query}", "--print",
                                "%(title)s|%(duration_string)s|%(webpage_url)s", "--no-playlist", "--no-warnings"],
                            stdout=subprocess.PIPE, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        hasil = []
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|")
                                if len(parts) == 3:
                                    title, dur, link = [p.strip()
                                                        for p in parts]
                                    hasil.append((title, dur, link))
                        url = pilih_dengan_fzf(hasil)
                        if not url:
                            continue
                    elif pilihan == "2":
                        query = input(colored("🔍 Masukkan judul atau kata kunci: ",
                                              "green", attrs=["bold"])).strip()
                        print(colored(f"\n{garis('=', 60)}", "cyan"))
                        print(colored(" Mencari Audio ".center(
                            60, " "), "yellow", attrs=["bold"]))
                        print(colored("Mohon tunggu sebentar...", "cyan"))
                        print(colored(garis('=', 60), "cyan"))

                        # Menjalankan pencarian dengan yt-dlp
                        result = subprocess.run(
                            ["yt-dlp", f"ytsearch10:{query}", "--print",
                                "%(title)s|%(duration_string)s|%(webpage_url)s", "--no-playlist", "--no-warnings"],
                            stdout=subprocess.PIPE, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        hasil = []
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|")
                                if len(parts) == 3:
                                    title, dur, link = [p.strip()
                                                        for p in parts]
                                    hasil.append((title, dur, link))

                        # Jika tidak ada hasil pencarian
                        if not hasil:
                            print(colored(
                                "❌ Tidak ada hasil pencarian. Coba dengan kata kunci yang lebih spesifik.", "red", attrs=["bold"]))
                            continue

                        # Menampilkan hasil pencarian dalam tabel
                        print(colored("\n🎶 Hasil Pencarian yang Ditemukan 🎶",
                                      "magenta", attrs=["bold"]))
                        print(colored(garis('-', 60), "cyan"))
                        table = [[
                            colored(f"{i+1}", "green", attrs=["bold"]),
                            colored(title, "white"),
                            colored(dur, "cyan")
                        ] for i, (title, dur, _) in enumerate(hasil)]
                        print(tabulate(table, headers=[
                            colored("#", "yellow", attrs=["bold"]),
                            colored("Judul", "yellow", attrs=["bold"]),
                            colored("Durasi", "yellow", attrs=["bold"])
                        ], tablefmt="rounded_grid", stralign="left"))
                        print(colored(garis('-', 60), "cyan"))
                        print(colored("[0] Cari judul lain",
                              "magenta", attrs=["bold"]))

                        # Memilih hasil pencarian
                        try:
                            idx = input(colored("🔢 Pilih nomor [1-{}] atau [0] untuk mencari judul lain (Tekan Enter untuk memilih yang pertama): ".format(len(hasil)),
                                                "green", attrs=["bold"])).strip()
                            if idx == "0":
                                continue
                            if not idx:
                                idx = 1
                            else:
                                idx = int(idx)
                            if not (1 <= idx <= len(hasil)):
                                print(colored(
                                    "⚠️ Nomor tidak valid. Pilih nomor yang ada dalam daftar.", "red", attrs=["bold"]))
                                continue
                            url = hasil[idx - 1][2]
                        except (ValueError, IndexError):
                            print(colored(
                                "❌ Input tidak valid. Harap masukkan nomor yang benar.", "red", attrs=["bold"]))
                            continue

                        # Lanjutkan dengan logika auto play atau pemutaran manual
                        auto_play = input(colored("\n🔁 Apakah Anda ingin memutar audio secara otomatis setelah memilih? (y/n): ",
                                                  "green", attrs=["bold"])).strip().lower()
                        if auto_play == 'y':
                            print(colored("\n🎧 Memulai pemutaran audio...",
                                          "blue", attrs=["bold"]))

                            def play_audio(index):
                                try:
                                    subprocess.run(
                                        ["mpv", "--no-video", hasil[index][2]])
                                except Exception as e:
                                    print(
                                        colored(f"❌ Gagal memutar audio: {str(e)}", "red"))
                            idx -= 1
                            while True:
                                play_audio(idx)
                                time.sleep(3)
                                idx += 1
                                if idx >= len(hasil):
                                    print(colored(
                                        "\n🔁 Sudah mencapai akhir daftar, kembali ke awal.", "yellow", attrs=["bold"]))
                                    idx = 0
                        else:
                            print(colored(
                                "\n❗ Anda dapat memulai pemutaran audio secara manual nanti.", "yellow"))
                    elif pilihan == "3":
                        url = input(colored("Masukkan link YouTube: ",
                                    "green", attrs=["bold"])).strip()
                    else:
                        print(colored("Pilihan tidak valid.", "red"))
                        continue
                    title, duration, uploader = get_metadata(url)
                    tampil_kontrol()
                    print(colored("▶ Now Playing:", "magenta"), colored(
                        f"{title} - {uploader} [{duration}]", "green"))
                    print(colored(garis("="), "cyan"), "\n")
                    play_mpv(url, title, duration, uploader)
                    while True:
                        aksi = ulangi_pemutaran()
                        if aksi == "1":
                            time.sleep(1)
                            play_mpv(url, title, duration, uploader)
                        elif aksi == "2":
                            break
                        elif aksi == "0":
                            print(colored("Keluar.", "red"))
                            sys.exit(0)
                        else:
                            print(colored("Pilihan tidak valid.", "red"))
                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    continue

            elif opsi == "2":
                try:
                    print(colored("\nPilih opsi untuk playlist YouTube:",
                          "yellow", attrs=["bold"]))
                    print(colored("1. Play dengan fzf", "green"))
                    print(colored("2. Play tanpa fzf", "green"))
                    print(colored("0. Kembali ke awal", "red"))
                    pilihan_playlist = input(
                        colored("Pilih opsi [0-2]: ", "cyan", attrs=["bold"])).strip()
                    if pilihan_playlist == "1":
                        query = input(
                            colored("Masukkan link playlist atau kata kunci: ", "green")).strip()
                        print(colored("Mengambil isi playlist...", "blue"))
                        result = subprocess.run(
                            ["yt-dlp", "--flat-playlist", "--print",
                                "%(title)s|%(duration_string)s|https://www.youtube.com/watch?v=%(id)s", query],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        hasil = []
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|")
                                if len(parts) == 3:
                                    title, dur, link = [p.strip()
                                                        for p in parts]
                                    hasil.append((title, dur, link))
                        url = pilih_dengan_fzf(hasil)
                        if not url:
                            continue
                        title, duration, uploader = get_metadata(url)
                        tampil_kontrol()
                        print(colored("▶ Now Playing:", "magenta"), colored(
                            f"{title} - {uploader} [{duration}]", "green"))
                        print(colored(garis("="), "cyan"), "\n")
                        play_mpv(url, title, duration, uploader)
                    elif pilihan_playlist == "2":
                        query = input(
                            colored("Masukkan link playlist: ", "green")).strip()
                        print(colored("Mengambil metadata video pertama...", "blue"))
                        result = subprocess.run(
                            ["yt-dlp", "--flat-playlist", "--print",
                                "https://www.youtube.com/watch?v=%(id)s", query],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        first_url = lines[0] if lines else query
                        title, duration, uploader = get_metadata(first_url)
                        tampil_kontrol()
                        print(colored("▶ Now Playing:", "magenta"), colored(
                            f"{title} - {uploader} [{duration}]", "green"))
                        print(colored(garis("="), "cyan"), "\n")
                        play_mpv(query, title, duration, uploader)
                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    continue

            elif opsi == "3":
                try:
                    print(colored("\nPilih opsi untuk mengunduh audio:",
                          "yellow", attrs=["bold"]))
                    print(colored("1. Buka dengan fzf", "green"))
                    print(colored("2. Buka tanpa fzf", "green"))
                    print(colored("0. Kembali ke awal", "red"))
                    pilihan_download = input(
                        colored("Pilih opsi [0-2]: ", "cyan", attrs=["bold"])).strip()
                    if pilihan_download == "0":
                        continue
                    elif pilihan_download in ["1", "2"]:
                        query = input(
                            colored("Masukkan judul atau link video/playlist: ", "green")).strip()
                        if query.startswith("http"):
                            url = query
                        else:
                            print(colored("Mencari...", "blue"))
                            result = subprocess.run(
                                ["yt-dlp", f"ytsearch10:{query}", "--print",
                                    "%(title)s|%(duration_string)s|%(webpage_url)s", "--no-playlist", "--no-warnings"],
                                stdout=subprocess.PIPE, text=True
                            )
                            lines = result.stdout.strip().splitlines()
                            hasil = []
                            for line in lines:
                                if "|" in line:
                                    parts = line.split("|")
                                    if len(parts) == 3:
                                        title, dur, link = [
                                            p.strip() for p in parts]
                                        hasil.append((title, dur, link))
                            if pilihan_download == "1":
                                url = pilih_dengan_fzf(hasil)
                                if not url:
                                    print(
                                        colored("Tidak ada video yang dipilih.", "red"))
                                    continue
                            elif pilihan_download == "2":
                                url = hasil[0][2] if hasil else None
                                if not url:
                                    print(
                                        colored("Tidak ada hasil pencarian.", "red"))
                                    continue
                        gunakan_fzf = pilihan_download == "1"
                        download_audio(url, gunakan_fzf=gunakan_fzf)
                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    continue

            elif opsi == "4":  # Opsi baru untuk Spotify
                try:
                    if not last_played:
                        spotify_link = input(colored(
                            "\nMasukkan link Spotify (playlist, album, artis, atau single): ", "green", attrs=["bold"])).strip()
                        last_played, downloaded_files = play_spotify_link(
                            spotify_link)
                    while True:
                        opsi_spotify = show_menu_spotify()
                        if opsi_spotify == "1":
                            if downloaded_files:
                                print(
                                    colored("\nMemutar ulang semua lagu...\n", "green"))
                                for mp3 in downloaded_files:
                                    if os.path.exists(mp3):
                                        play_mp3(mp3)
                            else:
                                print(
                                    colored("Tidak ada lagu untuk diputar.", "red"))
                        elif opsi_spotify == "2":
                            for f in downloaded_files:
                                if os.path.exists(f):
                                    print(
                                        colored(f"Menghapus file {f}...", "magenta"))
                                    os.remove(f)
                            last_played = None
                            downloaded_files = []
                            break
                        elif opsi_spotify == "3":
                            print(
                                colored("Lagu telah disimpan dan keluar.", "green"))
                            sys.exit(0)
                        elif opsi_spotify == "4":
                            print(colored("Kembali ke menu awal.", "green"))
                            break
                        elif opsi_spotify == "0":
                            for f in downloaded_files:
                                if os.path.exists(f):
                                    print(
                                        colored(f"Menghapus file {f}...", "magenta"))
                                    os.remove(f)
                            print(colored("Keluar dari program.", "green"))
                            sys.exit(0)
                        else:
                            print(colored("Opsi tidak valid. Coba lagi.", "red"))
                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    for f in downloaded_files:
                        if os.path.exists(f):
                            print(colored(f"Menghapus file {f}...", "magenta"))
                            os.remove(f)
                    last_played = None
                    downloaded_files = []
                    continue

            else:
                print(colored("Pilihan tidak valid.", "red"))

        except KeyboardInterrupt:
            print("\n" + colored("Terhenti. Keluar.", "red"))
            for f in downloaded_files:
                if os.path.exists(f):
                    print(colored(f"Menghapus file {f}...", "magenta"))
                    os.remove(f)
            sys.exit(0)


if __name__ == "__main__":
    main()
