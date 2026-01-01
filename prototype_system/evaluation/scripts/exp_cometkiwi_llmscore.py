import os
import json
from tqdm import tqdm
import time
import requests
import re

from comet import download_model, load_from_checkpoint

def calculate_cometkiwi():
    

    output_dir = "./evaluation/deepseek-v3"
    exp_dir = "./evaluation"

    model_path = download_model("Unbabel/wmt22-cometkiwi-da")
    model = load_from_checkpoint(model_path)

    cometkiwi_score = []
    score_path = os.path.join(exp_dir, "cometkiwi_score.json")

    for paper_folder in tqdm(os.listdir(output_dir), desc=f"Evaluating...", unit="paper"):
        paper_path = os.path.join(output_dir, paper_folder)
        data_path = os.path.join(paper_path, "merged_data.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        model_output = model.predict(data, batch_size=2, gpus=1)
        cometkiwi_score.append({
            "fold": paper_folder,
            "score": model_output["system_score"]
        })

        with open(score_path, 'w', encoding='utf-8') as f:
            json.dump(cometkiwi_score, f, ensure_ascii=False, indent=2)

def calculate_llmscore():
    
    outputs = "./outputs"

    scores_path = "./scores/llm_score.json"

    prompt = """
    You are a professional translation evaluator. Given an English source paragraph and its Chinese translation, evaluate the translation quality according to the following criteria:

    - **Faithfulness**: How accurately and completely does the translation convey the meaning of the source text?

    - **Fluency**: Is the translation natural, idiomatic, and grammatically correct in Chinese?

    - **Terminology and Formatting Consistency**: Are all technical terms translated correctly and consistently throughout the paragraph? Is the formatting—such as emphasis, symbols, references, and structural markers—preserved where applicable?

    - **Contextual Coherence**: Does the translation maintain logical flow, appropriate pronoun/reference usage, and contextual consistency across sentences within the paragraph?

    Score each dimension from 0 to 10. Then, compute a final overall score (0 to 10), reflecting the overall translation quality, and round it to one decimal place.

    **Only return the final overall score as a number. Do not include explanations, sub-scores, or any additional content.**

    """
    api_key = ""
    base_url = ""

    def extract_first_number(text: str) -> float:
        match = re.search(r'-?\d+(\.\d+)?', text)
        if match:
            return float(match.group())
        return "N/A"

    def request_gpt4o(src, tgt):
        """
        Requests the LLM to summarize the given text.
        """
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<en source>:\n{src}\n<zh translation>:\n{tgt}"
                }
            ],
            "temperature": 0.2,
            # "max_length": 100000,
            # "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                response = requests.post(base_url, json=payload, headers=headers, timeout=100)
                response.raise_for_status()  
                result = response.json()
                score = extract_first_number(result["choices"][0]["message"]["content"])
                if score == "N/A":
                    return "N/A"
                if score < 0 or score > 10:
                    return "N/A"
                
                return score
            except requests.exceptions.RequestException as e:
                if attempt < 3:
                    time.sleep(3)  
                else:
                    return "N/A"


    gpt4o_score_val = []
    for paper_folder in tqdm(os.listdir(outputs), desc=f"Evaluating...", unit="paper"):
        paper_path = os.path.join(outputs, paper_folder)
        data_path = os.path.join(paper_path, "sections_data.json")
        gpt4o_scores = []

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        merged_items = []
        i = 0
        while i < len(data):
            item1 = data[i]
            item2 = data[i+1] if i + 1 < len(data) else None

            merged_src = item1["src"]
            merged_mt = item1["mt"]

            if item2:
                merged_src += "\n" + item2["src"]
                merged_mt += "\n" + item2["mt"]

            merged_items.append({
                "src": merged_src,
                "mt": merged_mt
            })

            i += 2  

        for item in tqdm(merged_items, desc=f"Evaluating {paper_folder}...", unit="item"):
            per_data_score = request_gpt4o(item["src"], item["mt"])
            gpt4o_scores.append(per_data_score)

        valid_scores = [float(score) for score in gpt4o_scores if score != "N/A"]
        avg_score_paper = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

        gpt4o_score_val.append({
            "fold": paper_folder,
            "score": avg_score_paper
        })

        with open(scores_path, 'w', encoding='utf-8') as f:
            json.dump(gpt4o_score_val, f, ensure_ascii=False, indent=2)
