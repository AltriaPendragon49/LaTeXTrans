"""
Simplified LaTeX Utilities for Web Backend

This is a minimal version containing only essential functions for MVP:
- arXiv download functionality
- Basic file validation

Full utils.py will be integrated in later phases.
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List
import time
import logging

logger = logging.getLogger(__name__)


def get_tex_url(arxiv_id: str, headers: dict) -> str:
    """
    Get TeX source download link from arXiv
    
    Args:
        arxiv_id: arXiv paper ID
        headers: HTTP headers
    
    Returns:
        Download URL or empty string if not found
    """
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        resp = requests.get(abs_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch arXiv page for {arxiv_id}: {e}")
        return ""
    
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.find("a", class_="abs-button download-eprint")
    if link and link.get("href"):
        return f"https://arxiv.org{link['href']}"
    return ""


def is_already_downloaded(arxiv_id: str, save_dir: str) -> bool:
    """
    Check if tar.gz file or extracted directory already exists
    
    Args:
        arxiv_id: arXiv paper ID
        save_dir: Save directory
    
    Returns:
        True if already downloaded
    """
    tar_path = os.path.join(save_dir, f"{arxiv_id}.tar.gz")
    extracted_dir = os.path.join(save_dir, arxiv_id)
    return os.path.exists(tar_path) or os.path.isdir(extracted_dir)


def download_tex(arxiv_id: str, tex_url: str, save_dir: str, headers: dict) -> str:
    """
    Download TeX source .tar.gz file
    
    Args:
        arxiv_id: arXiv paper ID
        tex_url: Download URL
        save_dir: Save directory
        headers: HTTP headers
    
    Returns:
        Path to extracted directory
    
    Raises:
        Exception: If download fails
    """
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{arxiv_id}.tar.gz")

    try:
        logger.info(f"Downloading {arxiv_id} from {tex_url}")
        with requests.get(tex_url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("Content-Length", 0))
            
            downloaded = 0
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            logger.info(f"Downloaded {arxiv_id}: {downloaded}/{total_size} bytes")
        
        logger.info(f"[SUCCESS] {arxiv_id} successfully downloaded to {file_path}")
        return os.path.join(save_dir, arxiv_id)

    except requests.RequestException as e:
        logger.error(f"[FAIL] {arxiv_id} download failed: {e}")
        raise Exception(f"Download failed for {arxiv_id}: {e}")


def batch_download_arxiv_tex(arxiv_ids: List[str], save_dir: str = "./data/uploads") -> List[str]:
    """
    Batch download multiple arXiv paper TeX sources
    
    Args:
        arxiv_ids: List of arXiv IDs
        save_dir: Save directory
    
    Returns:
        List of paths to downloaded source directories
    """
    source_dirs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for arxiv_id in arxiv_ids:
        arxiv_id = arxiv_id.strip()
        
        # Check if already downloaded
        if is_already_downloaded(arxiv_id, save_dir):
            source_dir = os.path.join(save_dir, arxiv_id)
            source_dirs.append(source_dir)
            logger.info(f"[SKIP] Already downloaded: {arxiv_id}")
            continue

        # Get download URL
        tex_url = get_tex_url(arxiv_id, headers)
        if tex_url:
            try:
                source_dir = download_tex(arxiv_id, tex_url, save_dir, headers)
                source_dirs.append(source_dir)
            except Exception as e:
                logger.error(f"Failed to download {arxiv_id}: {e}")
                continue
        else:
            logger.warning(f"[SKIP] No TeX source found for {arxiv_id}")
            
        # Download PDF as backup
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_dir = os.path.join(save_dir, arxiv_id)
        pdf_path = os.path.join(pdf_dir, f"{arxiv_id}.pdf")
        os.makedirs(pdf_dir, exist_ok=True)

        try:
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"[SUCCESS] Downloaded PDF for {arxiv_id}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to download PDF for {arxiv_id}: {e}")

    return source_dirs


def get_arxiv_category(arxiv_ids: List[str]) -> dict:
    """
    Get arXiv categories for papers
    
    Args:
        arxiv_ids: List of arXiv IDs
    
    Returns:
        Dictionary mapping arxiv_id to list of categories
    """
    results = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for arxiv_id in arxiv_ids:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        categories = []

        try:
            resp = requests.get(abs_url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            subjects_div = soup.find("div", class_="subjects")
            if subjects_div:
                matches = re.findall(r"\(([a-z]+\.[A-Z]+)\)", subjects_div.text)
                categories.extend(matches)
            else:
                td_subjects = soup.find("td", class_="tablecell subjects")
                if td_subjects:
                    matches = re.findall(r'\(([a-z]+\.[A-Z]+)\)', td_subjects.text)
                    categories.extend(matches)

            if not categories:
                logger.warning(f"No categories found for {arxiv_id}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch categories for {arxiv_id}: {e}")
            categories = []

        results[arxiv_id] = categories
        time.sleep(1)  # Rate limiting

    return results


def is_valid_arxiv_id(id_str: str) -> bool:
    """
    Validate arXiv ID format
    
    Args:
        id_str: Potential arXiv ID
    
    Returns:
        True if valid format
    """
    # Modern format: YYYY.NNNNN or YYYY.NNNNNNN
    if re.match(r'^\d{4}\.\d{5,7}$', id_str):
        return True
    # Old format: subject/YYMMNNN (e.g., hep-th/9901001)
    if re.match(r'^[\w\-]+/\d{7}$', id_str):
        return True
    return False


def extract_arxiv_ids(arxiv_list: List[str]) -> List[str]:
    """
    Extract valid arXiv IDs from a list of strings/URLs
    
    Args:
        arxiv_list: List of arXiv IDs or URLs
    
    Returns:
        List of extracted valid arXiv IDs
    """
    ids = []
    for item in arxiv_list:
        if is_valid_arxiv_id(item):
            ids.append(item)
            continue

        # Try to extract from URL
        url_pattern = r'(?:arxiv\.org/)(?:abs|pdf|e-print)/([\w\-]+/\d{7}|\d{4}\.\d{5,7})(?:\.pdf)?'
        match = re.search(url_pattern, item)
        if match:
            ids.append(match.group(1))
    
    return ids
