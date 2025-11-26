import os
# 1. Triton 끄기
os.environ["UNSLOTH_USE_TRITON"] = "0" 

import torch

# ================= [★ 여기를 수정하세요] =================
# 이전 lambda 코드는 @torch.compile(옵션) 형태를 처리 못했습니다.
# 아래 함수는 어떤 형태로 호출되든 무조건 "그냥 통과시켜!"라고 처리합니다.

def no_op_compile(source_fn=None, *args, **kwargs):
    # Case A: @torch.compile(dynamic=True) 처럼 옵션만 주고 호출했을 때
    if source_fn is None:
        return lambda x: x # 나중에 함수가 들어오면 그대로 반환하는 함수를 줌
    # Case B: torch.compile(model) 처럼 바로 호출했을 때
    return source_fn # 들어온 걸 그대로 반환

torch.compile = no_op_compile
# =========================================================

import time
from unsloth import FastLanguageModel

# ==========================================
# 👇 여기서 테스트하고 싶은 모델의 주석(#)을 푸세요
# ==========================================

# 1. Meta Llama 3.2 (1B) - [속도 1위 / 밸런스]
# model_name = "meta-llama/Llama-3.2-1B-Instruct"

# 2. Qwen 2.5 Coder (1.5B) - [코딩 1위]
# model_name = "unsloth/Qwen2.5-Coder-1.5B-Instruct"

# 3. Google Gemma 2 (2B) - [문장력 우수 / 약간 무거움]
model_name = "unsloth/gemma-2-2b-it"

# 4. MS Phi-3.5 (3.8B) - [똑똑함 / 아주 무거움]
# model_name = "unsloth/Phi-3.5-mini-instruct"

# ==========================================

max_seq_length = 2048
load_in_4bit = True

print(f"\n🔄 [시작] {model_name} 로드 중...")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = model_name,
    max_seq_length = max_seq_length,
    dtype = None,
    load_in_4bit = load_in_4bit,
)
FastLanguageModel.for_inference(model)

# ★ 핵심 변경: 모델에 맞는 대화 형식을 자동으로 적용해줌
messages = [
    {"role": "user", "content": "C++로 피보나치 수열 함수를 짜고 원리를 길게 설명해줘."}
]
inputs = tokenizer.apply_chat_template(
    messages,
    tokenize = True,
    add_generation_prompt = True, # AI가 답변할 차례임을 알려줌
    return_tensors = "pt",
).to("cuda")

print("\n🧠 [테스트] 생성 시작 (Warm-up)...")
model.generate(inputs, max_new_tokens = 10, use_cache = True)

print("🚀 [측정] 진짜 속도 측정 시작...")
torch.cuda.synchronize()
start_time = time.time()

# 최대 500 토큰 생성
outputs = model.generate(inputs, max_new_tokens = 500, use_cache = True)

torch.cuda.synchronize()
end_time = time.time()

# 생성된 토큰 개수 (전체 - 질문 길이)
generated_tokens = outputs.shape[1] - inputs.shape[1]
duration = end_time - start_time
tps = generated_tokens / duration

# 답변 확인 (제대로 말했는지 앞부분만 출력)
decoded_output = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

print("\n" + "="*40)
print(f"🗣️ [답변 일부 확인]: {decoded_output[:100]}...") 
print("="*40)

print(f"\n📊 [최종 벤치마크 결과: {model_name}]")
print(f"• 총 생성 토큰 수: {generated_tokens} 개")
print(f"• 걸린 시간: {duration:.2f} 초")
print(f"• ⚡ TPS (초당 토큰 수): {tps:.2f} tokens/sec")
print("="*40)