import urllib.request
import xml.etree.ElementTree as ET

def fetch_arxiv():
    url = 'http://export.arxiv.org/api/query?search_query=cat:cs.CV+AND+ti:survey&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        count = 0
        with open('arxiv_surveys.md', 'w', encoding='utf-8') as f:
            f.write('# 二十篇带TeX源码的计算机领域综述 (arXiv IDs)\n\n')
            for entry in root.findall('atom:entry', ns):
                if count >= 20: break
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                id_node = entry.find('atom:id', ns).text
                arxiv_id = id_node.split('/abs/')[-1]
                f.write(f"- `{arxiv_id}`: {title}\n")
                count += 1
        print('Successfully wrote 20 surveys to arxiv_surveys.md')
    except Exception as e:
        print('Error arXiv:', e)

fetch_arxiv()
