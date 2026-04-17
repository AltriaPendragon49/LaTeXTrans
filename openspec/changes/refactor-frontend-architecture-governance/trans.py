import os
import shutil
from pathlib import Path

# Try to import deep-translator, if not available, provide instructions
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Error: 'deep-translator' library not found.")
    print("Please install it using: pip install deep-translator")
    exit(1)

def translate_markdown():
    # Get the directory where the script is located
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir / "translated_md"
    
    # Create the output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Initialize translator
    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    print(f"Starting translation from: {script_dir}")
    print(f"Output directory: {output_dir}")
    
    # Traverse all directories and files recursively
    # We use script_dir as root, excluding the output_dir itself
    for root, dirs, files in os.walk(script_dir):
        # Skip the output directory to avoid infinite loops or re-translating translated files
        if Path(root) == output_dir or output_dir in Path(root).parents:
            continue
            
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                
                # Prepare the new filename
                new_filename = file_path.stem + "_zh" + file_path.suffix
                target_path = output_dir / new_filename
                
                print(f"Translating: {file_path.relative_to(script_dir)} -> {new_filename}")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if not content.strip():
                        print(f"Skipping empty file: {file}")
                        continue
                        
                    # Translate content
                    # Note: deep-translator has a limit per request (usually 5000 chars)
                    # For a simple script, we handle it in one go if small, or could chunk it.
                    # Here we attempt to translate the whole content.
                    if len(content) > 4500:
                        # Simple chunking for larger files
                        translated_content = ""
                        chunks = [content[i:i+4500] for i in range(0, len(content), 4500)]
                        for chunk in chunks:
                            translated_content += translator.translate(chunk)
                    else:
                        translated_content = translator.translate(content)
                        
                    # Save to the new file (overwrite if exists)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(translated_content)
                        
                except Exception as e:
                    print(f"Failed to translate {file}: {e}")

    print("\nTranslation complete!")

if __name__ == "__main__":
    translate_markdown()
