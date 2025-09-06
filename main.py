import os
import re
import random
import string
import urllib.request
import time
import logging
from pathlib import Path
import sys

# --- Настройка логирования ---
logging.basicConfig(
    filename='Img_To_Local_Python.log',
    filemode="w",
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# --- Конфигурация ---
FOLDER_NAME = "External_Imgs_to_Local_Files"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"

# --- Папки (создадим в родительской папке текущей) ---
base_dir = Path.cwd()
dest_dir = base_dir.parent / FOLDER_NAME
dest_dir.mkdir(parents=True, exist_ok=True)

print(f"Folder for images and edited files: {dest_dir}")
logging.info(f"Folder for images and edited files: {dest_dir}")

# --- Регекс (ловит Постер: "URL" и markdown ![](...)) ---
# Обновленное регулярное выражение, чтобы захватить весь URL, 
# включая те, у которых нет стандартного расширения файла.
pattern = re.compile(
    rf'''(?xi)
    (?:                                             # Альтернатива 1: Постер: "URL" или Постер: URL
        Постер:\s*["']?(?P<url_p>https?://[^\s"']+)["']?
    )
    |
    (?:                                             # Альтернатива 2: markdown image ![alt](URL)
        !\[[^\]]*\]\((?P<url_m>https?://[^\s\)]+)\)
    )
    '''
)

# --- Утилиты ---
def random_prefix(n=8):
    return ''.join(random.choice(string.hexdigits) for _ in range(n))

# --- Создаёт словарь url -> локальное имя ---
class UrlDictCreator:
    def create(self, file_data):
        url_map = {}
        used_names = set()
        try:
            for m in pattern.finditer(file_data):
                url = m.group('url_p') or m.group('url_m')
                if not url:
                    continue
                
                # Генерируем уникальное имя файла и добавляем расширение .jpeg
                name = f"{random_prefix(8)}.jpeg"
                while name in used_names:
                    name = f"{random_prefix(8)}.jpeg"
                
                used_names.add(name)
                if url not in url_map:
                    url_map[url] = name
        except Exception:
            logging.exception("Error while creating url map")
        return url_map

# --- Скачивает картинки ---
class ImgDownloader:
    def download_images(self, url_dict, folder_path, user_agent):
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', user_agent)]
        urllib.request.install_opener(opener)
        
        for url, name in url_dict.items():
            dest = os.path.join(folder_path, name)
            try:
                print(f"Downloading {url} -> {dest}")
                urllib.request.urlretrieve(url, dest)
                print(f"Successfully downloaded {name}")
            except urllib.error.URLError as e:
                logging.error(f"URL Error for {url}: {e.reason}")
                print(f"URL Error for {url}: {e.reason}")
            except urllib.error.HTTPError as e:
                logging.error(f"HTTP Error for {url}: {e.code} {e.reason}")
                print(f"HTTP Error for {url}: {e.code} {e.reason}")
            except Exception as e:
                logging.exception(f"General error downloading {url}: {e}")
                print(f"General error downloading {url}: {e}")
            time.sleep(random.uniform(0.5, 1.5))

# --- Запись файлов ---
class FileWritter:
    def write_file(self, folder_path, filename, filedata):
        out_path = os.path.join(folder_path, filename)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(filedata)
            logging.info(f"Wrote edited file: {out_path}")
        except Exception:
            logging.exception(f"Error writing file {out_path}")

# --- Редактор содержимого (заменяет URL на [[name]]) ---
class FileDataEditor:
    def edit(self, file_data, url_dict, file_name):
        try:
            for url, name in url_dict.items():
                replacement = f"[[_resources/{stem}/{name}]]"
                file_data = file_data.replace(url, replacement)
                logging.info(f"Replaced {url} -> {replacement} in {file_name}")
                print(f"Replaced {url} -> {replacement}")
        except Exception:
            logging.exception("Error while editing file data")
        return file_data

# --- Открытие файла ---
class FileOpener:
    def open_and_read(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                logging.info(f"Opened {filename}")
                return f.read()
        except Exception:
            logging.exception(f"Error opening {filename}")
            return None

# --- Main loop ---
print("\nStarting processing markdown files...\n")
# Инициализируем загрузчик
downloader = ImgDownloader()

for path in base_dir.glob("*.md"):
    filename = path.name
    stem = path.stem # имя файла без расширения
    print(f"Processing {filename} ...")

    file_data = FileOpener().open_and_read(str(path))
    if file_data is None:
        print(f"Failed to read {filename}, skipping.")
        continue

    url_dict = UrlDictCreator().create(file_data)
    if not url_dict:
        logging.info(f"No image URLs found in {filename}")
        print(f"No image URLs found in {filename}")
        continue

    # --- создаём папку _resources/{stem} ---
    resources_folder = dest_dir / "_resources" / stem
    resources_folder.mkdir(parents=True, exist_ok=True)

    # Заменяем ссылки в тексте (на _resources/{stem}/filename.ext)
    edited_data = file_data
    for url, name in url_dict.items():
        replacement = f"[[_resources/{stem}/{name}]]"
        edited_data = edited_data.replace(url, replacement)
        logging.info(f"Replaced {url} -> {replacement} in {filename}")
        print(f"Replaced {url} -> {replacement}")

    # Скачиваем картинки в _resources/{stem}
    downloader.download_images(url_dict, str(resources_folder), USER_AGENT)

    # Сохраняем изменённый .md в External_Imgs_to_Local_Files
    FileWritter().write_file(str(dest_dir), filename, edited_data)

    print(f"Finished {filename}\n")

print("Done. Check folder:", dest_dir)
print("Log file:", Path.cwd() / "Img_To_Local_Python.log")

print("\nPress enter to close")

input()
