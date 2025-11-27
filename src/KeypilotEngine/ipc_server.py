import time
import win32pipe, win32file, pywintypes
import torch
from unsloth import FastLanguageModel

# ==========================================
# [설정] 파이프 이름 (C#이랑 똑같아야 함)
# ==========================================
PIPE_NAME = r'\\.\pipe\keypilot_pipe'
MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"

def load_model():
    print("🔄 [Init] 모델 로딩 중... (4-bit)")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_ID,
        max_seq_length = 2048,
        dtype = None,
        load_in_4bit = True,
    )
    FastLanguageModel.for_inference(model)
    print("✅ [Init] 모델 로드 완료! 연결 대기 중...")
    return model, tokenizer

def run_server():
    model, tokenizer = load_model()
    
    print(f"📡 [Server] 파이프 생성: {PIPE_NAME}")
    
    while True:
        try:
            # 1. 파이프 생성 (Named Pipe)
            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX, # 양방향 통신
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1, 65536, 65536, 0, None
            )
            
            # 2. 클라이언트(C#) 접속 대기 (여기서 멈춰있음)
            print("⏳ [Wait] 클라이언트 접속 대기 중...")
            win32pipe.ConnectNamedPipe(pipe, None)
            print("🔗 [Connect] 클라이언트 연결됨!")

            # 3. 데이터 수신 (Read)
            # C#에서 보낸 텍스트 읽기
            resp = win32file.ReadFile(pipe, 64*1024)
            user_input = resp[1].decode('utf-8')
            print(f"📩 [Recv] 받은 내용: {user_input}")

            # 4. AI 추론 (Generate)
            # (속도를 위해 간단한 템플릿 적용)
            messages = [{"role": "user", "content": user_input}]
            inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")
            
            outputs = model.generate(inputs, max_new_tokens=50, use_cache=True) # 속도 위해 50토큰만 생성
            response_text = tokenizer.batch_decode(outputs)[0].split("<|start_header_id|>assistant<|end_header_id|>")[-1].strip()
            
            print(f"📤 [Send] 보낼 내용: {response_text[:30]}...") # 로그엔 앞부분만 출력

            # 5. 데이터 송신 (Write)
            # C#으로 결과 보내기
            win32file.WriteFile(pipe, response_text.encode('utf-8'))

        except pywintypes.error as e:
            if e.args[0] == 109: # Broken Pipe
                print("❌ [Error] 클라이언트 연결 끊김")
            else:
                print(f"❌ [Error] 파이프 에러: {e}")
        finally:
            # 연결 해제 후 다시 대기 루프
            win32file.CloseHandle(pipe)

if __name__ == "__main__":
    run_server()