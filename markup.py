import json
import os
import streamlit as st

# Настройка широкого экрана
st.set_page_config(layout="wide", page_title="OCR Dataset Annotator")

# Инициализация сессионного состояния
if "dataset" not in st.session_state:
    st.session_state.dataset = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "file_path" not in st.session_state:
    st.session_state.file_path = ""


def load_dataset(path):
    """Загрузка JSONL файла в память."""
    if not os.path.exists(path):
        st.error(f"Файл {path} не найден.")
        return []
    
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def save_dataset():
    """Сохранение всего датасета обратно в JSONL."""
    path = st.session_state.file_path
    if not path:
        return
    
    with open(path, "w", encoding="utf-8") as f:
        for item in st.session_state.dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    st.toast("Прогресс автоматически сохранен!", icon="💾")


def next_image():
    """Переход к следующему изображению с сохранением текста."""
    current_idx = st.session_state.current_index
    input_text = st.session_state.get(f"suffix_input_{current_idx}", "")
    st.session_state.dataset[current_idx]["suffix"] = input_text
    
    save_dataset()
    
    if st.session_state.current_index < len(st.session_state.dataset) - 1:
        st.session_state.current_index += 1
    else:
        st.success("Вы дошли до конца датасета!")


def delete_current_item(img_path):
    """Синхронное удаление файла картинки и записи в JSONL."""
    idx = st.session_state.current_index
    
    # 1. Удаляем файл с диска, если он существует
    if os.path.exists(img_path):
        try:
            os.remove(img_path)
            st.toast(f"Файл удален: {os.path.basename(img_path)}", icon="🗑️")
        except Exception as e:
            st.error(f"Не удалось удалить файл: {e}")
            return
    else:
        st.toast("Файл картинки не найден на диске, удаляем только запись", icon="⚠️")

    # 2. Удаляем запись из структуры в памяти
    st.session_state.dataset.pop(idx)
    
    # 3. Синхронизируем изменения с файлом JSONL
    save_dataset()
    
    # 4. Корректируем индекс текущей позиции
    if len(st.session_state.dataset) == 0:
        st.session_state.current_index = 0
        st.success("Датасет полностью пуст!")
    elif st.session_state.current_index >= len(st.session_state.dataset):
        # Если удалили самый последний элемент, смещаем указатель назад
        st.session_state.current_index = len(st.session_state.dataset) - 1


# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    file_input = st.text_input(
        "Путь к JSONL файлу:", 
        value="dataset.jsonl",
        placeholder="path/to/dataset.jsonl"
    )
    
    base_dir = st.text_input(
        "Корневая папка с картинками (если пути относительные):", 
        value="",
        placeholder="Оставьте пустой, если пути полные"
    )

    if st.button("🔄 Загрузить / Обновить датасет", use_container_width=True):
        st.session_state.file_path = file_input
        st.session_state.dataset = load_dataset(file_input)
        st.session_state.current_index = 0
        st.rerun()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
st.title("📝 Разметка и валидация OCR датасета")

if not st.session_state.dataset:
    st.info("Пожалуйста, укажите путь к JSONL файлу в боковой панели и нажмите 'Загрузить'.")
else:
    dataset = st.session_state.dataset
    idx = st.session_state.current_index
    total = len(dataset)
    
    current_item = dataset[idx]
    
    st.progress((idx + 1) / total)
    st.write(f"**Элемент:** {idx + 1} из {total} | **Файл:** `{current_item['image']}`")
    
    img_path = current_item["image"]
    if base_dir:
        img_path = os.path.join(base_dir, img_path)
        
    col1, col2 = st.columns(2)
    
    # Левая колонка: Изображение
    with col1:
        st.subheader("🖼️ Изображение")
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.error(f"Изображение не найдено по пути:\n`{img_path}`")
            
    # Правая колонка: Инструменты и кнопка удаления
    with col2:
        st.subheader("✍️ Текст (Suffix)")
        st.caption(f"Prefix модели: `{current_item.get('prefix', 'ocr')}`")
        
        edited_suffix = st.text_area(
            "Распознанный текст / Поле для ввода:",
            value=current_item.get("suffix", ""),
            height=250,
            key=f"suffix_input_{idx}"
        )
        
        st.write("---")
        
        # Разделяем зону действий на две кнопки: Продолжить и Удалить
        btn_col1, btn_col2 = st.columns([2, 1])
        
        with btn_col1:
            st.button("➡️ Сохранить и Далее", on_click=next_image, use_container_width=True)
            
        with btn_col2:
            # Кнопка удаления с подтверждением во избежание случайных нажатий
            if st.button("❌ Удалить элемент", use_container_width=True, type="secondary"):
                delete_current_item(img_path)
                st.rerun()

    # Навигация (назад/вперед) внизу
    st.write("")
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        if st.button("⬅️ Предыдущий", disabled=(idx == 0), use_container_width=True):
            st.session_state.dataset[idx]["suffix"] = st.session_state[f"suffix_input_{idx}"]
            save_dataset()
            st.session_state.current_index -= 1
            st.rerun()
            
    with nav_col3:
        if st.button("Пропустить (Вперед) ➡️", disabled=(idx == total - 1), use_container_width=True):
            st.session_state.dataset[idx]["suffix"] = st.session_state[f"suffix_input_{idx}"]
            save_dataset()
            st.session_state.current_index += 1
            st.rerun()
