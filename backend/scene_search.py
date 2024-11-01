# backend/scene_search.py
import json
from typing import List

import vertexai
import vertexai.preview.generative_models as generative_models
from vertexai.preview.generative_models import GenerativeModel
from google.cloud import storage

from . import PROJECT_ID, DATASTORE_ID, LOCATION
from .search_document import search_documents_by_query
from .utils import generate_download_signed_url_v4
from .prompt_content_search import PROMPT_CONTENT_SEARCH

from google import auth

# from google.oauth2 import service_account
# credentials = service_account.Credentials.from_service_account_file('service_account_key.json')
credentials, project_id = auth.default()
credentials.refresh(auth.transport.requests.Request())

# --- グローバル変数 ---
vertexai.init(project=PROJECT_ID, location='us-central1')
model_pro = GenerativeModel('gemini-1.5-pro')
model_flash = GenerativeModel('gemini-1.5-flash')


def generate_text(prompt: str, model: GenerativeModel = model_pro, temperature: float = 0.4, top_p: float = 0.4) -> str:
    """Gemini でテキストを生成する

    Args:
        prompt: 入力プロンプト
        model: 利用する Gemini モデル
        temperature: 生成テキストのランダム性
        top_p: 生成テキストの多様性

    Returns:
        生成されたテキスト
    """
    responses = model.generate_content(
        prompt,
        generation_config={
            'max_output_tokens': 8192,
            'temperature': temperature,
            'top_p': top_p
        },
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        stream=True,
    )

    result = ''
    for response in responses:
        try:
            print(response.text, end='')
            result += response.text
        except Exception as e:
            print(e)
            break

    return result


def load_json(text: str) -> dict:
    """JSON文字列をパースする

    Args:
        text: JSON 文字列

    Returns:
        パースされた JSON オブジェクト
    """
    text = text.replace('```json', '').replace('```', '').replace('\n', ' ')
    return json.loads(text)


def search_scene(query: str, top_n: int = 1, model: GenerativeModel = model_flash) -> List[dict]:
    """シーン検索を実行する

    Args:
        query: 検索クエリ
        top_n: 検索対象とする動画の数
        model: 利用する Gemini モデル

    Returns:
        検索結果のリスト
    """
    response = search_documents_by_query(query, show_summary=False)
    storage_client = storage.Client(credentials=credentials)
    results = []
    for doc_id in range(min(top_n, len(response.results))):
        meta_uri = response.results[doc_id].document.derived_struct_data['link']
        title = response.results[doc_id].document.derived_struct_data['title']
        print(f'meta_uri: {meta_uri}')
        bucket_name = meta_uri.split("//")[1].split("/", 1)[0]
        blob_name = meta_uri.replace(f'gs://{bucket_name}/', '')
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # download_to_filename を使わずに、blob から直接テキストデータを読み込む
        metatext = blob.download_as_text()

        # blob.download_to_filename('metadata.txt')
        # with open('metadata.txt', 'r') as f:
        #     metatext = f.read()

        prompt = PROMPT_CONTENT_SEARCH.format(query=query, metatext=metatext)
        temperature = 0.4
        result = None
        while temperature < 1.0:
            try:
                movie_blob_name = meta_uri.replace('gs://minitap-genai-app-dev-handson/metadata/', 'mp4/s_').replace('.txt', '.mp4')
                print(f'movie_blob_name: {movie_blob_name}')
                signed_url = generate_download_signed_url_v4(bucket_name, movie_blob_name)
                result_str = generate_text(prompt, model=model, temperature=temperature)
                result = load_json(result_str)
                results.extend([dict(r, signed_url=signed_url, title=title) for r in result])
                break
            except Exception as e:
                print(e)
                temperature += 0.05
        if temperature < 1.0:
            print('\n=====')
    return results
