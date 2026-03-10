import os
import json

outputs_dir = r"d:\future\antigravity\LaTexTrans\backend\data\outputs"

total_blocks = 0
fallbacks_analyzed = []

for root, _, files in os.walk(outputs_dir):
    for filename in files:
        if filename in ["sections_map.json", "envs_map.json"]:
            p = os.path.join(root, filename)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = list(data.values())
                    else:
                        continue
                        
                    for v in items:
                        total_blocks += 1
                        status = v.get("translation_status", "")
                        has_fallback_reason = "fallback_reason" in v
                        if "fallback" in status or has_fallback_reason or status == "ultimate_downgrade_applied":
                            id_str = v.get('id', v.get('section', 'unknown'))
                            msg = v.get("fallback_reason", "")
                            
                            # Categorize
                            reason_tag = v.get("repair_rejection_reason")
                            if status == "ultimate_downgrade_applied":
                                if reason_tag:
                                    cat = f"Ultimate Downgrade ({reason_tag})"
                                else:
                                    cat = "Ultimate Downgrade"
                            elif msg == "invariant_raw_structure_exposed":
                                cat = "Invariant Structure (Expected Pass-through)"
                            else:
                                if reason_tag:
                                    cat = f"Silent Fallback ({status}) ({reason_tag})"
                                else:
                                    cat = f"Silent Fallback (Status: {status})"
                                
                            fallbacks_analyzed.append((cat, os.path.basename(root), id_str, msg))
            except Exception as e:
                pass

with open(r"d:\future\antigravity\LaTexTrans\scripts\clean_results2.txt", "w", encoding="utf-8") as out:
    for cat, doc, idx, msg in sorted(fallbacks_analyzed):
        out.write(f"[{cat}] {doc} ID {idx} - {msg}\n")
    
    out.write(f"\nTotal blocks: {total_blocks}\n")
    out.write(f"Total fallback-related: {len(fallbacks_analyzed)}\n")
    from collections import Counter
    c = Counter([x[0] for x in fallbacks_analyzed])
    for k, v in c.items():
        out.write(f"{k}: {v}\n")
