import os
import json
import shutil
import re
from pathlib import Path
from datetime import datetime

class ResultSyncer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.configs_path = self.project_root / 'backend' / 'data' / 'task_configs'
        self.pdf_out_path = self.project_root / 'pdf'
        self.md_path = self.project_root / '待测论文.md'
        
        self.pdf_out_path.mkdir(exist_ok=True)
        
        self.task_results = {} # arxiv_id -> {task_id, status, error, pdf_path, output_dir}
        self.arxiv_to_task_id = {} # For update_arxiv_tasks functionality

    def parse_logs(self):
        print("Scaning task configs and logs...")
        if not self.configs_path.exists():
            print(f"Configs path not found: {self.configs_path}")
            return

        # 1. Get all configs, sort by timestamp to get the latest for each arxiv_id
        config_files = sorted(list(self.configs_path.glob('*.json')), key=lambda p: p.name, reverse=True)
        
        processed_arxivs = set()

        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                arxiv_id = data.get('arxiv_id')
                task_id = data.get('metadata', {}).get('task_id', '')
                output_dir = data.get('additional_info', {}).get('output_dir')
                
                if not arxiv_id or not task_id:
                    continue
                
                t_id_short = task_id[:8]
                self.arxiv_to_task_id.setdefault(arxiv_id, set()).add(t_id_short)

                # Only process the latest result for categorization
                if arxiv_id in processed_arxivs:
                    continue
                processed_arxivs.add(arxiv_id)

                if not output_dir or not os.path.exists(output_dir):
                    continue

                # The log might be in a subfolder like zh_2312.13895
                log_path = None
                output_path = Path(output_dir)
                
                # Check direct folder
                if (output_path / 'task_log.json').exists():
                    log_path = output_path / 'task_log.json'
                else:
                    # Check subfolders
                    for sub in output_path.iterdir():
                        if sub.is_dir() and (sub / 'task_log.json').exists():
                            log_path = sub / 'task_log.json'
                            break

                status = "unknown"
                error_msg = ""
                pdf_found = None

                if log_path and log_path.exists():
                    try:
                        with open(log_path, 'r', encoding='utf-8') as lf:
                            logs = json.load(lf)
                        
                        for entry in reversed(logs):
                            event = entry.get('event')
                            if event == 'compilation_completed':
                                status = "perfect"
                                pdf_found = entry.get('pdf_path')
                                break
                            elif event == 'compilation_completed_with_warnings':
                                status = "warning"
                                pdf_found = entry.get('pdf_path')
                                error_msg = entry.get('warnings', '')
                                break
                            elif event == 'compilation_failed':
                                status = "failed"
                                error_msg = entry.get('error_summary', '') or entry.get('warnings', '')
                                break
                    except Exception as e:
                        print(f"Error reading log {log_path}: {e}")

                self.task_results[arxiv_id] = {
                    'task_id': t_id_short,
                    'status': status,
                    'error': error_msg,
                    'pdf_path': pdf_found,
                    'output_dir': output_dir
                }
            except Exception as e:
                print(f"Error processing {config_file}: {e}")

    def extract_pdfs(self):
        print("Extracting PDFs...")
        for arxiv_id, res in self.task_results.items():
            pdf_path = res.get('pdf_path')
            if pdf_path and os.path.exists(pdf_path):
                target_name = os.path.basename(pdf_path)
                # Ensure the name is unique if multiple tasks for same arxiv (though we pick latest)
                shutil.copy2(pdf_path, self.pdf_out_path / target_name)
                # print(f"Copied {target_name} to pdf/")

    def update_markdown(self):
        print("Updating 待测论文.md...")
        if not self.md_path.exists():
            print("待测论文.md not found.")
            return

        with open(self.md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 1. Update task IDs (update_arxiv_tasks functionality)
        updated_lines = []
        delimiter = "_"
        for line in lines:
            new_line = line
            for a_id, t_ids in self.arxiv_to_task_id.items():
                if a_id in line:
                    for t_id in t_ids:
                        if t_id not in new_line:
                            base = new_line.rstrip('\n')
                            if not base.endswith(delimiter):
                                new_line = f"{base}{delimiter}{t_id}\n"
                            else:
                                new_line = f"{base}{t_id}\n"
            updated_lines.append(new_line)

        # 2. Add Categorization Sections
        # We'll create a summary section at the end if it doesn't exist
        sections = {
            "完美": [],
            "有警告生成pdf": [],
            "编译失败": []
        }

        for arxiv_id, res in self.task_results.items():
            t_id = res['task_id']
            status = res['status']
            err = res['error'].replace('\n', ' ')
            entry = f"{arxiv_id}_{t_id} {err}".strip()
            
            if status == "perfect":
                sections["完美"].append(entry)
            elif status == "warning":
                sections["有警告生成pdf"].append(entry)
            elif status == "failed":
                sections["编译失败"].append(entry)

        # Remove previous "自动同步结果" section if it exists to refresh
        content = "".join(updated_lines)
        if "## 自动同步结果" in content:
            content = content.split("## 自动同步结果")[0]
        
        content = content.rstrip() + "\n\n## 自动同步结果\n"
        content += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for name, items in sections.items():
            content += f"### {name} ({len(items)})\n"
            for item in items:
                content += f"{item}\n"
            content += "\n"

        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def run(self):
        self.parse_logs()
        self.extract_pdfs()
        self.update_markdown()
        print("Sync complete.")

if __name__ == "__main__":
    syncer = ResultSyncer()
    syncer.run()
