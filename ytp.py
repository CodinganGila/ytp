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


def get_metadata(url):
    try:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--print", "%(title)s||%(duration_string)s||%(uploader)s",
            "--no-warnings",
            "--playlist-items", "1"
        ]

        if os.path.exists("cookies.txt"):
            cmd.extend(["--cookies", "cookies.txt"])

        cmd.append(url)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split("||")
            if len(parts) == 3:
                title = parts[0] or "Unknown"
                duration = parts[1] or "??:??"
                uploader = parts[2] or "Unknown"
                return title, duration, uploader
    except Exception as e:
        print(colored(f"Gagal mengambil metadata: {str(e)}", "red"))

    return "Unknown", "??:??", "Unknown"


def play_mpv(url, title, duration, uploader):
    ipc_socket = create_ipc_socket()
    cmd = [
        "mpv", "--no-video",
        f"--input-ipc-server={ipc_socket}",
        "--term-playing-msg=▶ Now Playing: ${media-title}",
        "--force-window=no",
        "--ytdl-format=bestaudio",
    ]

    if os.path.exists("cookies.txt"):
        cmd.append("--ytdl-raw-options=cookies=cookies.txt")

    cmd.append(url)

    print(colored("\n▶ Now Playing:", "magenta"), colored(
        f"{title} - {uploader} [{duration}]", "green"))
    print(colored(garis("="), "cyan"))

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
        print("\n" + colored("Pemutaran dihentikan.", "red"))
        process.terminate()
    finally:
        hapus_socket(ipc_socket)


def monitor_status(ipc_socket):
    import json
    while os.path.exists(ipc_socket):
        try:
            res = subprocess.run(
                ["socat", "-", f"UNIX-CONNECT:{ipc_socket}"],
                input='{"command": ["get_property", "time-pos"]}\n',
                text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )

            lines = res.stdout.strip().splitlines()
            for line in lines:
                if '"data"' in line:
                    try:
                        t = float(line.split('"data":')[1].split("}")[0])
                        mins, secs = divmod(int(t), 60)
                        print(f"Waktu: {mins:02}:{secs:02}", end="\r")
                    except:
                        pass
            time.sleep(1)
        except Exception:
            break


def ulangi_pemutaran():
    print(colored("\nPilih aksi:", "cyan", attrs=["bold"]))
    print(colored("1. Ulangi pemutaran", "green"))
    print(colored("2. Kembali ke awal", "green"))
    print(colored("0. Keluar", "red"))
    try:
        return input(colored("Pilih aksi [0-2]: ", "cyan", attrs=["bold"])).strip().lower()
    except KeyboardInterrupt:
        print("\n" + colored("Operasi dihentikan.", "red"))
        return "0"


def pilih_dengan_fzf(hasil):
    try:
        daftar = "\n".join(
            [f"{title} | {dur} | {url}" for title, dur, url in hasil])
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
        print(colored(f"Gagal menggunakan fzf: {str(e)}", "red"))
    return None


def download_audio(url, gunakan_fzf=False):
    try:
        if "playlist" in url.lower():
            print(colored("\nMemproses playlist...", "blue"))
            cmd = [
                "yt-dlp",
                "--flat-playlist",
                "--print", "%(title)s|%(duration_string)s|%(url)s",
                "--no-warnings"
            ]

            if os.path.exists("cookies.txt"):
                cmd.extend(["--cookies", "cookies.txt"])

            cmd.append(url)

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            lines = result.stdout.strip().splitlines()
            hasil = []
            for line in lines:
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) == 3:
                        hasil.append(
                            (parts[0].strip(), parts[1].strip(), parts[2].strip()))

            if gunakan_fzf:
                url_video = pilih_dengan_fzf(hasil)
                if not url_video:
                    print(colored("Tidak ada video yang dipilih.", "red"))
                    return
            else:
                url_video = hasil[0][2] if hasil else None
                if not url_video:
                    print(colored("Playlist kosong.", "red"))
                    return
        else:
            url_video = url

        print(colored("\nMemulai pengunduhan...", "blue"))
        cmd = [
            "yt-dlp",
            "-x",  # extract audio
            "--audio-format", "mp3",
            "--embed-thumbnail",
            "--add-metadata",
            "--output", "%(title)s.%(ext)s",
        ]

        if os.path.exists("cookies.txt"):
            cmd.extend(["--cookies", "cookies.txt"])

        cmd.append(url_video)

        try:
            subprocess.run(cmd, check=True)
            print(colored("✓ Unduhan selesai!", "green", attrs=["bold"]))
        except subprocess.CalledProcessError as e:
            print(colored(f"✗ Gagal mengunduh: {
                  str(e)}", "red", attrs=["bold"]))

    except KeyboardInterrupt:
        print("\n" + colored("Unduhan dibatalkan.", "red"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def main():
    # Peringatan jika cookies.txt tidak ada
    if not os.path.exists("cookies.txt"):
        print(colored(
            "\n⚠ Warning: cookies.txt tidak ditemukan. Beberapa video mungkin tidak dapat diakses.", "yellow"))
        time.sleep(2)

    while True:
        try:
            header()
            opsi = input(
                colored("Pilih opsi [0-2]: ", "cyan", attrs=["bold"])).strip()

            if opsi == "0":
                print(colored("Keluar dari program.", "red"))
                sys.exit(0)

            elif opsi == "1":
                try:
                    query = input(
                        colored("Masukkan judul atau link: ", "green", attrs=["bold"])).strip()

                    if query.startswith(("http://", "https://")):
                        url = query
                    else:
                        print(colored("Mencari di YouTube...", "blue"))
                        cmd = [
                            "yt-dlp",
                            f"ytsearch10:{query}",
                            "--print", "%(title)s|%(duration_string)s|%(url)s",
                            "--no-playlist",
                            "--no-warnings"
                        ]

                        if os.path.exists("cookies.txt"):
                            cmd.extend(["--cookies", "cookies.txt"])

                        result = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            text=True
                        )

                        lines = result.stdout.strip().splitlines()
                        hasil = []
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|")
                                if len(parts) == 3:
                                    hasil.append(
                                        (parts[0].strip(), parts[1].strip(), parts[2].strip()))

                        if not hasil:
                            print(colored("Tidak ada hasil ditemukan.", "red"))
                            continue

                        url = pilih_dengan_fzf(hasil)
                        if not url:
                            continue

                    title, duration, uploader = get_metadata(url)
                    tampil_kontrol()
                    play_mpv(url, title, duration, uploader)

                    while True:
                        aksi = ulangi_pemutaran()
                        if aksi == "1":
                            play_mpv(url, title, duration, uploader)
                        elif aksi == "2":
                            break
                        elif aksi == "0":
                            sys.exit(0)
                        else:
                            print(colored("Input tidak valid.", "red"))

                except KeyboardInterrupt:
                    print("\n" + colored("Kembali ke menu utama.", "yellow"))
                    continue

            elif opsi == "2":
                try:
                    print(colored("\nPilih mode playlist:",
                          "yellow", attrs=["bold"]))
                    print(colored("1. Pilih video dengan fzf", "green"))
                    print(colored("2. Putar otomatis", "green"))
                    print(colored("0. Kembali", "red"))

                    while True:
                        mode = input(
                            colored("Pilihan [0-2]: ", "cyan")).strip()

                        if mode == "0":
                            break  # Kembali ke menu utama
                        elif mode == "1" or mode == "2":
                            # lanjut ke input playlist & pemutaran
                            query = input(
                                colored("Masukkan link playlist: ", "green")).strip()

                            if mode == "1":
                                query = input(
                                    colored("Masukkan link playlist: ", "green")).strip()
                                print(colored("Memuat daftar video...", "blue"))
                                cmd = [
                                    "yt-dlp",
                                    "--flat-playlist",
                                    "--print", "%(title)s|%(duration_string)s|%(url)s",
                                    "--no-warnings"
                                ]

                                if os.path.exists("cookies.txt"):
                                    cmd.extend(["--cookies", "cookies.txt"])

                                result = subprocess.run(
                                    cmd + [query],
                                    stdout=subprocess.PIPE,
                                    text=True
                                )

                                lines = result.stdout.strip().splitlines()
                                hasil = []
                                for line in lines:
                                    if "|" in line:
                                        parts = line.split("|")
                                        if len(parts) == 3:
                                            hasil.append(
                                                (parts[0].strip(), parts[1].strip(), parts[2].strip()))

                                if not hasil:
                                    print(
                                        colored("Playlist kosong atau tidak dapat diakses.", "red"))
                                    continue

                                url = pilih_dengan_fzf(hasil)
                                if not url:
                                    continue

                                title, duration, uploader = get_metadata(url)
                                tampil_kontrol()
                                play_mpv(url, title, duration, uploader)

                            elif mode == "2":
                                query = input(
                                    colored("Masukkan link playlist: ", "green")).strip()
                                title, duration, uploader = get_metadata(query)
                                tampil_kontrol()
                                play_mpv(query, title, duration, uploader)

                        else:
                            print(
                                colored("Pilihan tidak valid, silakan pilih antara 0-2.", "red"))

                except KeyboardInterrupt:
                    print("\n" + colored("Operasi dibatalkan.", "red"))
                    continue

            elif opsi == "3":
                try:
                    print(colored("\nPilih mode unduh:",
                          "yellow", attrs=["bold"]))
                    print(colored("1. Pilih video dengan fzf", "green"))
                    print(colored("2. Unduh langsung", "green"))
                    print(colored("0. Kembali", "red"))

                    while True:
                        mode = input(
                            colored("Pilihan [0-2]: ", "cyan")).strip()
                        if mode == "0":
                            break
                        elif mode in ["1", "2"]:
                            query = input(
                                colored("Masukkan judul/link: ", "green")).strip()
                            break
                        else:
                            print(
                                colored("Pilihan tidak valid, silakan pilih antara 0-2.", "red"))

                    if mode == "1":
                        if query.startswith(("http://", "https://")):
                            if "playlist" in query.lower():
                                download_audio(query, gunakan_fzf=True)
                            else:
                                print(
                                    colored("Link langsung, mengunduh tanpa fzf...", "yellow"))
                                download_audio(query)
                        else:
                            print(colored("Mencari di YouTube...", "blue"))
                            cmd = [
                                "yt-dlp",
                                f"ytsearch10:{query}",
                                "--print", "%(title)s|%(duration_string)s|%(url)s",
                                "--no-playlist",
                                "--no-warnings"
                            ]

                            if os.path.exists("cookies.txt"):
                                cmd.extend(["--cookies", "cookies.txt"])

                            result = subprocess.run(
                                cmd,
                                stdout=subprocess.PIPE,
                                text=True
                            )

                            lines = result.stdout.strip().splitlines()
                            hasil = []
                            for line in lines:
                                if "|" in line:
                                    parts = line.split("|")
                                    if len(parts) == 3:
                                        hasil.append(
                                            (parts[0].strip(), parts[1].strip(), parts[2].strip()))

                            if not hasil:
                                print(colored("Tidak ada hasil ditemukan.", "red"))
                                continue

                            url = pilih_dengan_fzf(hasil)
                            if url:
                                download_audio(url)

                    elif mode == "2":
                        download_audio(query)

                except KeyboardInterrupt:
                    print("\n" + colored("Unduhan dibatalkan.", "red"))
                    continue

            else:
                print(colored("Pilihan tidak valid.", "red"))
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n" + colored("Keluar dari program.", "red"))
            sys.exit(0)
        except Exception as e:
            print(colored(f"Error: {str(e)}", "red"))
            time.sleep(2)


if __name__ == "__main__":
    main()
