import urllib.request
import xml.etree.ElementTree as ET
import random
import time
from pathlib import Path
from datetime import datetime

def has_tex_source(arxiv_id):
    """
    Checks if an arXiv paper has LaTeX source available.
    Recent papers (last 4 years) in math/physics almost always do,
    unless they are specifically marked as 'PDF only'.
    We do a HEAD request to the source URL to be sure.
    """
    source_url = f'https://arxiv.org/src/{arxiv_id}'
    try:
        req = urllib.request.Request(source_url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True
    except Exception:
        pass
    return False

def fetch_arxiv_ids(category, count=50, years=4):
    """
    Fetches random arXiv IDs for a given category from the last N years
    with guaranteed LaTeX source.
    """
    current_year = datetime.now().year
    start_year = current_year - years
    
    base_url = 'http://export.arxiv.org/api/query?'
    # Increase max_results to compensate for filtering
    query = f'search_query=cat:{category}*+AND+submittedDate:[{start_year}01010000+TO+{current_year}12312359]&start=0&max_results=500'
    
    url = base_url + query
    print(f"Fetching from: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

    root = ET.fromstring(xml_data)
    namespace = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
    candidates = []
    for entry in root.findall('arxiv:entry', namespace):
        # 1. Check comments for "PDF only"
        comment = entry.find('arxiv:comment', namespace)
        if comment is not None and ('pdf only' in comment.text.lower()):
            continue
            
        id_url = entry.find('arxiv:id', namespace).text
        arxiv_id = id_url.split('/abs/')[-1].split('v')[0]
        candidates.append(arxiv_id)
    
    print(f"Found {len(candidates)} candidates for {category}. Verifying texsource...")
    
    # Randomly shuffle and check until we have enough
    random.shuffle(candidates)
    
    valid_ids = []
    for aid in candidates:
        if len(valid_ids) >= count:
            break
        
        if has_tex_source(aid):
            valid_ids.append(aid)
            print(f"[{len(valid_ids)}/{count}] Valid: {aid}")
            time.sleep(0.3) # Avoid hitting arXiv too hard
        else:
            print(f"Skipping (no src): {aid}")
            
    return valid_ids

def append_to_md(ids, title):
    md_path = Path(__file__).parent.parent / '待测论文.md'
    if not md_path.exists():
        print(f"Error: {md_path} does not exist.")
        return

    with open(md_path, 'a', encoding='utf-8') as f:
        f.write(f"\n\n### {title} (随机获取 {len(ids)} 篇)\n")
        for aid in ids:
            f.write(f"{aid}\n")
    print(f"Appended {len(ids)} IDs to {md_path}")

def main():
    print("Starting arXiv ID fetcher (Math only)...")
    
    # 100 Math IDs
    print("Fetching 100 Math IDs...")
    math_ids = fetch_arxiv_ids('math', 100)
    if math_ids:
        append_to_md(math_ids, "随机数学论文")
    
    print("Done!")

if __name__ == "__main__":
    main()
