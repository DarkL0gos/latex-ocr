import fitz  # PyMuPDF
from PIL import Image
import os
import json
import argparse
import sys


# Скрипт для автоматической нарезки pdf файлов на чанки для 
# обучения и для создания json файла
# использование: 
# python prepare_pdf.py my_notes.pdf --single - если одна страница = одна страница документа
# python prepare_pdf.py my_notes.pdf - если на странице один разворот
# python prepare_pdf.py old_book.pdf --chunks 8 - для мелкого текста






def process_pdf(pdf_path, chunks_v=4, is_spread=True):
    # 1. Формируем имена на основе названия файла
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = f"dataset_{base_name}"
    images_dir = os.path.join(output_dir, f"images_{base_name}")
    jsonl_path = os.path.join(output_dir, f"{base_name}.jsonl")

    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    doc = fitz.open(pdf_path)
    dataset_entries = []

    print(f"Обработка: {pdf_path} ({len(doc)} стр.)")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Высокое разрешение для мелкого почерка
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 2. Обработка разворота (сплит пополам)
        working_images = []
        if is_spread:
            mid = img.width // 2
            working_images.append(("left", img.crop((0, 0, mid, img.height))))
            working_images.append(("right", img.crop((mid, 0, img.width, img.height))))
        else:
            working_images.append(("full", img))

        # 3. Нарезка на горизонтальные блоки
        for side, side_img in working_images:
            h_chunk = side_img.height // chunks_v
            for i in range(chunks_v):
                top = i * h_chunk
                bottom = (i + 1) * h_chunk
                chunk_img = side_img.crop((0, top, side_img.width, bottom))
                
                img_filename = f"pg{page_num}_{side}_part{i}.png"
                img_path = os.path.join(images_dir, img_filename)
                chunk_img.save(img_path)

                # Сохраняем относительный путь для удобства обучения
                dataset_entries.append({
                    "image": f"images_{base_name}/{img_filename}",
                    "prefix": "ocr",
                    "suffix": "" # Сюда нужно будет вставить ваш текст
                })

    # 4. Сохранение JSONL
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for entry in dataset_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"Готово! Папка: {output_dir}")
    print(f"Создано фрагментов: {len(dataset_entries)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Разрезка PDF на фрагменты для PaliGemma")
    parser.add_argument("pdf", help="Путь к PDF файлу")
    parser.add_argument("--single", action="store_false", dest="spread", help="Если скан — одна страница, а не разворот")
    parser.add_argument("--chunks", type=int, default=4, help="На сколько частей резать страницу по горизонтали")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf):
        print(f"Ошибка: Файл {args.pdf} не найден.")
        sys.exit(1)

    process_pdf(args.pdf, chunks_v=args.chunks, is_spread=args.spread)
