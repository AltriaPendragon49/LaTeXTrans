import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator
from tqdm import tqdm

# ================= 配置区域 =================
SOURCE_EXT = '.md'
TARGET_SUFFIX = '_CN.md'
MAX_CHUNK_SIZE = 3500  # 稍微留余量，防止超出 Google 限制
MAX_WORKERS = 3        # 并发数（建议 1-5，太高容易被 Google 封 IP）
# ===========================================

def translate_chunk(text):
    """翻译单个文本块，带重试机制"""
    if not text or not text.strip():
        return text
    
    retries = 3
    for attempt in range(retries):
        try:
            translator = GoogleTranslator(source='auto', target='zh-CN')
            result = translator.translate(text)
            if result:
                return str(result)
            raise ValueError("Empty response")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return f"\n[翻译失败保留原文: {str(e)[:20]}]\n" + text
    return text

def split_text_into_chunks(text, max_size):
    """将文本按段落切分，确保每一块不超限"""
    if not text: return []
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0

    for p in paragraphs:
        if current_length + len(p) + 1 > max_size:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [p]
            current_length = len(p)
        else:
            current_chunk.append(p)
            current_length += len(p) + 1

    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    return chunks

def process_markdown(content):
    """解析并保护代码块，多线程翻译文本"""
    # 正则：同时匹配 ```代码块``` 和 `行内代码`
    code_pattern = r'(```[\s\S]*?```|`.*?`) '
    parts = re.split(code_pattern, content)
    parts = [p if p is not None else "" for p in parts]
    
    text_indices = [i for i in range(len(parts)) if i % 2 == 0 and parts[i].strip()]
    tasks = []
    chunk_mapping = {} 
    
    for idx in text_indices:
        raw_text = parts[idx]
        chunks = split_text_into_chunks(raw_text, MAX_CHUNK_SIZE)
        chunk_mapping[idx] = chunks[:] # 预填原文
        for c_idx, chunk in enumerate(chunks):
            if chunk.strip():
                tasks.append({'part_idx': idx, 'chunk_idx': c_idx, 'text': chunk})

    if tasks:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_task = {executor.submit(translate_chunk, t['text']): t for t in tasks}
            for future in tqdm(as_completed(future_to_task), total=len(tasks), desc="   翻译中", leave=False):
                task = future_to_task[future]
                try:
                    res = future.result()
                    chunk_mapping[task['part_idx']][task['chunk_idx']] = str(res)
                except:
                    pass

    final_parts = list(parts)
    for idx in text_indices:
        final_parts[idx] = '\n'.join([str(s) for s in chunk_mapping[idx]])

    return ''.join(final_parts)

def main():
    root_dir = os.getcwd()
    all_files = []

    # 递归查找所有 MD 文件
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(SOURCE_EXT) and not f.endswith(TARGET_SUFFIX):
                all_files.append(os.path.join(dirpath, f))
    
    if not all_files:
        print("💡 当前目录下没有找到可翻译的 Markdown 文件。")
        return

    print(f"🚀 准备处理 {len(all_files)} 个文件 (并发: {MAX_WORKERS}，模式: 强制覆盖)...")
    print("-" * 50)

    for file_path in all_files:
        dir_name = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        target_path = os.path.join(dir_name, f"{base_name}{TARGET_SUFFIX}")

        # 无论是否存在，都进行处理（实现强制覆盖）
        rel_path = os.path.relpath(file_path, root_dir)
        print(f"📄 正在翻译: {rel_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            start_time = time.time()
            new_content = process_markdown(content)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            elapsed = time.time() - start_time
            print(f"✅ 已覆盖输出: {os.path.basename(target_path)} (耗时: {elapsed:.1f}s)")
            
        except Exception as e:
            print(f"❌ 出错: {rel_path} \n   原因: {e}")

if __name__ == "__main__":
    main()