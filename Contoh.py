import os
import sys
import subprocess

def cls():
    os.system("clear")

def main_menu():
    cls()
    print("""
╔════════════════════════╗
║     🎵 Musik Menu      ║
╠════════════════════════╣
║ 1. Play Musik          ║
║ 2. Play Playlist       ║
║ 3. Download Musik      ║
║ 0. Keluar              ║
╚════════════════════════╝
""")
    return input("Pilih opsi: ")

def search_youtube(query):
    print("🔍 Mencari...")
    cmd = f"yt-dlp 'ytsearch10:{query}' --print '%(title)s | %(webpage_url)s'"
    hasil = subprocess.check_output(cmd, shell=True).decode().strip().split('\n')
    pilihan = "\n".join(hasil)
    pilihan_terpilih = subprocess.run("fzf", input=pilihan.encode(), stdout=subprocess.PIPE).stdout.decode().strip()
    if not pilihan_terpilih:
        print("❌ Tidak ada yang dipilih.")
        sys.exit()
    return pilihan_terpilih.split(" | ")[-1]

def play_music():
    query = input("Masukkan judul atau link: ").strip()
    if "youtube.com" in query or "youtu.be" in query:
        url = query
    else:
        url = search_youtube(query)
    print("🎧 Memutar musik...")
    os.system(f"mpv --no-video --ytdl-format=bestaudio {url}")

def play_playlist():
    url = input("Masukkan link playlist YouTube: ").strip()
    print("📜 Memutar playlist...")
    os.system(f"mpv --no-video --ytdl-format=bestaudio --playlist-start=1 {url}")

def download_music():
    query = input("Masukkan judul atau link: ").strip()
    if "youtube.com" in query or "youtu.be" in query:
        url = query
    else:
        url = search_youtube(query)

    print("⬇️  Mengunduh musik...")
    os.system(f"yt-dlp -x --audio-format mp3 {url}")

def main():
    while True:
        choice = main_menu()
        if choice == "1":
            play_music()
        elif choice == "2":
            play_playlist()
        elif choice == "3":
            download_music()
        elif choice == "0":
            print("👋 Keluar...")
            break
        else:
            print("❌ Pilihan tidak valid.")
        input("\nTekan Enter untuk kembali ke menu...")

if __name__ == "__main__":
    main()
