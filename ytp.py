import subprocess
import sys
import os
import time
import tempfile
from threading import Thread
from termcolor import colored
import pyfiglet

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
    print(colored("0. Keluar", "red"))
    print(colored(garis("-"), "cyan"))

def tampil_kontrol():
    print(colored(garis(), "cyan"))
    print(colored(" Kontrol Pemutaran MPV ".center(60, "="), "green", attrs=["bold"]))
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

    print(colored("▶ Now Playing:", "magenta"), colored(f"{title} - {uploader} [{duration}]", "green"))
    print(colored(garis("="), "cyan"), "\n")

    Thread(target=monitor_status, args=(ipc_socket,), daemon=True).start()
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n" + colored("Terhenti. Keluar.", "red"))
        process.terminate()
    hapus_socket(ipc_socket)

def monitor_status(ipc_socket):
    import json
    while True:
        try:
            for prop in ["time-pos", "duration", "media-title"]:
                subprocess.run(["socat", "-", f"UNIX-CONNECT:{ipc_socket}"],
                    input=json.dumps({"command": ["observe_property", 1, prop]}) + "\n",
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
                print(f"{mins:02}:{secs:02} / {dur_m:02}:{dur_s:02} ({percent}%)", end="\r")
            time.sleep(1)
        except Exception:
            break

def get_metadata(url):
    result = subprocess.run(
        ["yt-dlp", "--cookies", "cookies.txt", "-e", "--get-duration", "--get-uploader", url],
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
        daftar = "\n".join([f"{title} | {dur} | {url}" for title, dur, url in hasil])
        fzf = subprocess.run(
            ["fzf", "--prompt=◉ Pilih: "],
            input=daftar,
            stdout=subprocess.PIPE,
            text=True
        )
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
        if "playlist" in url:  # Deteksi apakah URL adalah playlist
            print(colored("\nPilih video untuk diunduh:", "yellow", attrs=["bold"]))
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print", "%(title)s|%(duration_string)s|https://www.youtube.com/watch?v=%(id)s", url],
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
                    print(colored("Tidak ada video yang dipilih, kembali ke menu.", "red"))
                    return
            else:
                # Pilih video pertama tanpa fzf
                url_video = hasil[0][2] if hasil else None
                if not url_video:
                    print(colored("Playlist kosong atau tidak ada video yang dapat dipilih.", "red"))
                    return

            print(colored("\nMengunduh audio (otomatis kualitas terbaik)...", "blue", attrs=["bold"]))
            cmd = [
                "yt-dlp",
                "-x",  # extract audio
                "--embed-thumbnail",
                "--add-metadata",
                "--output", "%(title)s.%(ext)s",
                url_video
            ]
            try:
                subprocess.run(cmd, check=True)
                print(colored("✓ Unduhan selesai!", "green", attrs=["bold"]))
            except subprocess.CalledProcessError:
                print(colored("✗ Gagal mengunduh audio.", "red", attrs=["bold"]))
        else:
            # Mengunduh audio dari link biasa
            print(colored("\nMengunduh audio (otomatis kualitas terbaik)...", "blue", attrs=["bold"]))
            cmd = [
                "yt-dlp",
                "-x",  # extract audio
                "--embed-thumbnail",
                "--add-metadata",
                "--output", "%(title)s.%(ext)s",
                url
            ]
            try:
                subprocess.run(cmd, check=True)
                print(colored("✓ Unduhan selesai!", "green", attrs=["bold"]))
            except subprocess.CalledProcessError:
                print(colored("✗ Gagal mengunduh audio.", "red", attrs=["bold"]))
    except KeyboardInterrupt:
        print("\n" + colored("Unduhan dihentikan.", "red"))

def main():
    while True:
        try:
            header()
            opsi = input(colored("Pilih opsi [0-3]: ", "cyan", attrs=["bold"])).strip()

            if opsi == "0":
                print(colored("Keluar.", "red"))
                sys.exit(0)

            elif opsi == "1":
                try:
                    query = input(colored("Masukkan judul atau link: ", "green", attrs=["bold"])).strip()
                    if query.startswith("http"):
                        url = query
                    else:
                        print(colored("Mencari...", "blue"))
                        result = subprocess.run(
                             ["yt-dlp", f"ytsearch10:{query}", "--print","%(title)s|%(duration_string)s|%(webpage_url)s", "--no-playlist", "--no-warnings"],
                            stdout=subprocess.PIPE, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        hasil = []
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|")
                                if len(parts) == 3:
                                    title, dur, link = [p.strip() for p in parts]
                                    hasil.append((title, dur, link))

                        url = pilih_dengan_fzf(hasil)
                        if not url:
                            continue

                    title, duration, uploader = get_metadata(url)
                    tampil_kontrol()
                    print(colored("▶ Now Playing:", "magenta"), colored(f"{title} - {uploader} [{duration}]", "green"))
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
                    print(colored("\nPilih opsi untuk playlist YouTube:", "yellow", attrs=["bold"]))
                    print(colored("1. Play dengan fzf", "green"))
                    print(colored("2. Play tanpa fzf", "green"))
                    print(colored("0. Kembali ke awal", "red"))
                    pilihan_playlist = input(colored("Pilih opsi [0-2]: ", "cyan", attrs=["bold"])).strip()

                    if pilihan_playlist == "1":
                        query = input(colored("Masukkan link playlist atau kata kunci: ", "green")).strip()
                        print(colored("Mengambil isi playlist...", "blue"))
                        result = subprocess.run(
                            ["yt-dlp", "--flat-playlist", "--print", "%(title)s|%(duration_string)s|https://www.youtube.com/watch?v=%(id)s", query],
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

                        url = pilih_dengan_fzf(hasil)
                        if not url:
                            continue

                        title, duration, uploader = get_metadata(url)
                        tampil_kontrol()
                        print(colored("▶ Now Playing:", "magenta"), colored(f"{title} - {uploader} [{duration}]", "green"))
                        print(colored(garis("="), "cyan"), "\n")
                        play_mpv(url, title, duration, uploader)

                    elif pilihan_playlist == "2":
                        query = input(colored("Masukkan link playlist: ", "green")).strip()
                        print(colored("Mengambil metadata video pertama...", "blue"))
                        result = subprocess.run(
                            ["yt-dlp", "--flat-playlist", "--print", "https://www.youtube.com/watch?v=%(id)s", query],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                        )
                        lines = result.stdout.strip().splitlines()
                        first_url = lines[0] if lines else query

                        title, duration, uploader = get_metadata(first_url)
                        tampil_kontrol()
                        print(colored("▶ Now Playing:", "magenta"), colored(f"{title} - {uploader} [{duration}]", "green"))
                        print(colored(garis("="), "cyan"), "\n")
                        play_mpv(query, title, duration, uploader)

                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    continue

            elif opsi == "3":
                try:
                    print(colored("\nPilih opsi untuk mengunduh audio:", "yellow", attrs=["bold"]))
                    print(colored("1. Buka dengan fzf", "green"))
                    print(colored("2. Buka tanpa fzf", "green"))
                    print(colored("0. Kembali ke awal", "red"))
                    pilihan_download = input(colored("Pilih opsi [0-2]: ", "cyan", attrs=["bold"])).strip()

                    if pilihan_download == "0":
                        continue

                    elif pilihan_download in ["1", "2"]:
                        query = input(colored("Masukkan judul atau link video/playlist: ", "green")).strip()

                        if query.startswith("http"):
                            url = query
                        else:
                            print(colored("Mencari...", "blue"))
                            result = subprocess.run(
                                ["yt-dlp", f"ytsearch10:{query}", "--print", "%(title)s|%(duration_string)s|%(webpage_url)s", "--no-playlist", "--no-warnings"],
                                stdout=subprocess.PIPE, text=True
                            )
                            lines = result.stdout.strip().splitlines()
                            hasil = []
                            for line in lines:
                                if "|" in line:
                                    parts = line.split("|")
                                    if len(parts) == 3:
                                        title, dur, link = [p.strip() for p in parts]
                                        hasil.append((title, dur, link))
                                                
                            if pilihan_download == "1":
                                url = pilih_dengan_fzf(hasil)
                                if not url:
                                    print(colored("Tidak ada video yang dipilih.", "red"))
                                    continue
                            elif pilihan_download == "2":
                                url = hasil[0][2] if hasil else None
                                if not url:
                                    print(colored("Tidak ada hasil pencarian.", "red"))
                                    continue
                                    
                        gunakan_fzf = pilihan_download == "1"
                        download_audio(url, gunakan_fzf=gunakan_fzf)
                                                                            
                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dihentikan.", "red"))
                    continue

            else:
                print(colored("Pilihan tidak valid.", "red"))

        except KeyboardInterrupt:
            print("\n" + colored("Terhenti. Keluar.", "red"))
            sys.exit(0)


if __name__ == "__main__":
    main()
