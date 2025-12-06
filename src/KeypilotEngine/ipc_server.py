import socket
import torch
import json
import re
from unsloth import FastLanguageModel
from english_words import get_english_words_set

HOST = '127.0.0.1'
PORT = 5000 
# 속도와 영어 실력 밸런스가 좋은 Llama 3.2 유지
MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"

ENGLISH_WORDS = sorted(list(get_english_words_set(['web2'], lower=False)))

def load_model():
    print(f"🔄 [Init] {MODEL_ID} 로딩 중...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_ID,
        max_seq_length = 2048,
        dtype = None,
        load_in_4bit = True,
    )
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token
    FastLanguageModel.for_inference(model)
    print("✅ [Init] 모델 로드 완료!")
    return model, tokenizer

def search_dictionary(prefix, limit=12):
    prefix_lower = prefix.lower()
    results = []
    for word in ENGLISH_WORDS:
        if word.lower().startswith(prefix_lower):
            if word.lower() == prefix_lower: continue
            results.append(word)
            if len(results) >= limit: break
    return results

def run_server():
    model, tokenizer = load_model()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    server_socket.settimeout(None) 
    
    print(f"📡 [Server] AI 자동완성 엔진 대기 중 ({HOST}:{PORT})")

    while True:
        client_socket = None
        try:
            client_socket, addr = server_socket.accept()
            
            data = client_socket.recv(65536)
            if not data:
                client_socket.close()
                continue
            
            user_input = data.decode('utf-8')
            print(f"📩 [입력] '{user_input}'")

            candidates = set()
            
            # 공백으로 끝나면 '다음 단어 예측', 아니면 '현재 단어 완성'
            is_next_word_mode = user_input.endswith(" ")
            
            # 1. 사전 검색 (단어 완성 모드일 때만)
            if not is_next_word_mode:
                last_chunk = user_input.split()[-1] if user_input.strip() else ""
                if len(last_chunk) >= 1:
                    dic_results = search_dictionary(last_chunk, limit=8)
                    for word in dic_results:
                        candidates.add(word)

            # 2. AI 추론 (부족하거나, 다음 단어 예측일 때)
            if len(candidates) < 12 or is_next_word_mode:
                inputs = tokenizer(user_input, return_tensors="pt").to("cuda")
                
                outputs = model.generate(
                    **inputs, 
                    max_new_tokens=10,       # ★ 수정: 5 -> 10 (단어 잘림 방지)
                    num_return_sequences=8, 
                    do_sample=True,
                    temperature=0.6,
                    top_k=40,
                    repetition_penalty=1.2,  # ★ 수정: 앵무새 방지
                    pad_token_id=tokenizer.eos_token_id
                )
                
                for output in outputs:
                    generated_text = tokenizer.decode(output[inputs['input_ids'].shape[1]:], skip_special_tokens=True)
                    
                    # 1. 앞뒤 공백 정리
                    stripped_text = generated_text.lstrip() 
                    # 2. 첫 단어만 가져오기
                    first_word = stripped_text.split()[0] if stripped_text else ""
                    # 3. 순수 알파벳과 하이픈, 아포스트로피만 허용
                    clean_word = re.sub(r"[^a-zA-Z\-\']", "", first_word)
                    
                    if not clean_word: continue

                    # ★ [수정] 1글자 필터링 (a, I 제외하고 다 버림)
                    if len(clean_word) == 1 and clean_word not in ["a", "I"]:
                        continue

                    if is_next_word_mode:
                        # "I want " -> "to"
                        candidates.add(clean_word)
                    else:
                        # "wa" -> "want"
                        last_chunk = user_input.split()[-1]
                        if clean_word.lower().startswith(last_chunk.lower()):
                             candidates.add(clean_word)
                        else:
                             candidates.add(last_chunk + clean_word)

            # 3. 정렬 및 전송
            # 길이 순서대로 정렬하되, 너무 긴 단어(20자 이상)는 뒤로 보냄
            final_list = sorted(list(candidates), key=lambda x: (len(x) > 20, len(x)))[:12]
            
            json_response = json.dumps(final_list)
            print(f"📤 [전송] {json_response}")
            
            client_socket.sendall(json_response.encode('utf-8'))

        except Exception as e:
            print(f"⚠️ 에러: {e}")
        finally:
            if client_socket: client_socket.close()

if __name__ == "__main__":
    run_server()