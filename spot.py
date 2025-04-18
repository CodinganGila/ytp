import subprocess
import sys
import os
import time
from termcolor import colored
from tabulate import tabulate

def play_mp3(mp3):
    print(colored(f"\nMemutar {mp3}...\n", "green"))
    subprocess.run(["mpv", mp3])

def wait_for_downloads(expected_count, timeout=180):
    print(f"\nMenunggu {expected_count} file mp3 selesai diunduh...\n")
    elapsed = 0
    while elapsed < timeout:
        mp3_files = sorted([f for f in os.listdir() if f.endswith(".mp3")])
        if len(mp3_files) >= expected_count:
            print(colored("Menemukan file mp3:", "cyan", attrs=["bold"]))
            table = [[i+1, f] for i, f in enumerate(mp3_files)]
            print(tabulate(table, headers=["#", "Nama File"], tablefmt="fancy_grid"))
            return mp3_files
        time.sleep(2)
        elapsed += 2
    return sorted([f for f in os.listdir() if f.endswith(".mp3")])

def estimate_song_count(link):
    return 4

def play_spotify_link(link):
    try:
        print(colored("\nMengunduh lagu dari Spotify...\n", "cyan", attrs=["bold"]))
        subprocess.Popen(f"spotdl {link}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

def show_menu():
    print(colored("\nMenu setelah lagu diputar:", "blue", attrs=["bold"]))
    print(colored("1. Putar kembali semua lagu", "cyan"))
    print(colored("2. Masukkan link Spotify baru", "cyan"))
    print(colored("3. Simpan lagu dan keluar", "cyan"))
    print(colored("0. Keluar", "cyan"))
    return input(colored("Pilih opsi: ", "yellow"))

if __name__ == "__main__":
    last_played = None
    downloaded_files = []

    while True:
        if not last_played:
            if len(sys.argv) == 2:
                spotify_link = sys.argv[1]
            else:
                spotify_link = input(colored("\nMasukkan link Spotify (playlist, album, artis, atau single): ", "blue"))
            last_played, downloaded_files = play_spotify_link(spotify_link)

        while True:  # Membuat loop menu agar tetap aktif
            opsi = show_menu()
            if opsi == "1":
                if downloaded_files:
                    print(colored("\nMemutar ulang semua lagu...\n", "green"))
                    for mp3 in downloaded_files:
                        if os.path.exists(mp3):
                            play_mp3(mp3)
                else:
                    print(colored("Tidak ada lagu untuk diputar.", "red"))
            elif opsi == "2":
                # Hapus semua file sebelum lanjut
                for f in downloaded_files:
                    if os.path.exists(f):
                        print(colored(f"Menghapus file {f}...", "magenta"))
                        os.remove(f)
                last_played = None
                downloaded_files = []
                break  # Keluar dari loop dan minta link Spotify baru
            elif opsi == "3":
                print(colored("Lagu telah disimpan dan keluar.", "green"))
                sys.exit(0)  # Keluar dari program tanpa menghapus file
            elif opsi == "0":
                for f in downloaded_files:
                    if os.path.exists(f):
                        print(colored(f"Menghapus file {f}...", "magenta"))
                        os.remove(f)
                print(colored("Keluar dari program.", "green"))
                sys.exit(0)  # Keluar dari program
            else:
                print(colored("Opsi tidak valid. Coba lagi.", "red"))
