from podcastfy.client import generate_podcast
import os

custom_config = {
    "word_count": 20000,
    "conversation_style": ["casual"],
    "podcast_name": "生成AIポッドキャスト",
    "creativity": 1,
    "output_language": "ja",
    "default_tts_model": "openai",
    "model_name": "openai/o3-mini",
    "text_to_speech": {
        "output_directories": {
            "audio": ".",
            "transcripts": "."
        },
        "model": "gpt-4o-mini-tts",
    }
}

# OPENAI_API_KEY を環境変数から取得
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("OPENAI_API_KEY")

# api_key_label を指定し、generate_podcastを呼び出す
# https://urltomarkdown.com/ 
with open("doc.md", "r", encoding="utf-8") as f:
    doc_md_content = f.read()

generate_podcast(
    text=doc_md_content,
    conversation_config=custom_config,
    llm_model_name="openai/o1",
    api_key_label="OPENAI_API_KEY",
    tts_model="openai",
    longform=True
)
