import torch
from unsloth import FastLanguageModel

# ==========================================
# 🛠️ 환경 검증용 스크립트 (Environment Verification)
# 목표: 4070 GPU 인식 여부, 4-bit 양자화 로드, 추론 성공 여부 확인
# ==========================================

def main():
    # 1. GPU 확인
    if not torch.cuda.is_available():
        print("❌ [Error] CUDA(GPU)가 감지되지 않았습니다.")
        return
    
    print(f"✅ [System] 감지된 GPU: {torch.cuda.get_device_name(0)}")

    # 2. 모델 설정 (Llama-3.2-1B)
    model_name = "meta-llama/Llama-3.2-1B-Instruct"
    max_seq_length = 2048
    load_in_4bit = True # ★ 핵심: 4비트 양자화 (VRAM 절약 확인용)

    print(f"⬇️ [Download] {model_name} 모델 로드 중...")

    # 3. 모델 로드
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = model_name,
            max_seq_length = max_seq_length,
            dtype = None,
            load_in_4bit = load_in_4bit,
        )
        print("✅ [Success] 모델 로드 완료! (VRAM 점유 확인 필요)")
    except Exception as e:
        print(f"❌ [Error] 모델 로드 실패: {e}")
        return

    # 4. 추론 테스트 (Inference)
    # Instruct 모델 포맷을 사용하여 질문
    prompt_template = """<|start_header_id|>user<|end_header_id|>
{}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>"""

    user_input = "C++로 'Hello Keypilot'을 출력하는 코드를 작성해줘."
    formatted_prompt = prompt_template.format(user_input)

    print("🧠 [Inference] 답변 생성 시도 중...")
    
    FastLanguageModel.for_inference(model) # 추론 모드 전환 (속도 최적화)
    inputs = tokenizer([formatted_prompt], return_tensors = "pt").to("cuda")

    outputs = model.generate(**inputs, max_new_tokens = 128, use_cache = True)
    result = tokenizer.batch_decode(outputs)
    
    # 결과 파싱 및 출력
    final_answer = result[0].split("<|start_header_id|>assistant<|end_header_id|>")[-1]
    
    print("\n" + "="*40)
    print(f"[AI 응답 결과]\n{final_answer.strip()}")
    print("="*40)
    print("✅ 환경 설정 검증이 완료되었습니다.")

if __name__ == "__main__":
    main()