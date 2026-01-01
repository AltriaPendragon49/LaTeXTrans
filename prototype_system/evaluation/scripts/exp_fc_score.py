import os

def find_log_file(build_dir):
    if not os.path.exists(build_dir):
        return None
    for fname in os.listdir(build_dir):
        if fname.endswith('.log'):
            return os.path.join(build_dir, fname)
    return None

def check_success_file(folder_path):
    file_path = os.path.join(folder_path, 'success.txt')
    if file_path:
        return True
    else:
        return False

def if_compiled_successfully(count, folder_path):
    if check_success_file(folder_path) or count == 0:
        return True
    else:
        return False

def analyze_latex_logs(root_dir):
    scores = []
    for paper_dir in os.listdir(root_dir)[:50]:
        paper_path = os.path.join(root_dir, paper_dir)
        if not os.path.isdir(paper_path):
            continue

        subdirs = [d for d in os.listdir(paper_path) if os.path.isdir(os.path.join(paper_path, d))]
        if not subdirs:
            continue
        source_dir = os.path.join(paper_path, subdirs[0])

        build_path = os.path.join(source_dir, "build_lualatex")
        log_path = find_log_file(build_path)

        if not log_path:
            build_path = os.path.join(source_dir, "build")
            log_path = find_log_file(build_path)

        if not log_path:
            print(paper_path)
            score = 0
            scores.append(score)
            # num -= 1
            continue

        error_count = 0
        warning_count = 0

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'Error' in line:
                    error_count += 1
                elif 'Warning' in line:
                    warning_count += 1

        score = 100 - 10 * error_count - 2 * warning_count + (20 if if_compiled_successfully(error_count,
                                                                                           source_dir
                                                                                           ) else 0)
        score = max(0, min(score, 100))
        scores.append(score)

    avg_score = sum(scores) / 50
    print(avg_score)
    return avg_score

llms = ["deepseek-v3","gpt-4o"]

for llm in llms:
    foldname = "outputs_" + llm
    foldpath = os.path.join("LaTexTrans", foldname)
    print(llm)
    analyze_latex_logs(foldpath)

