import torch
import sys
import platform
import psutil
import os

def print_info():
    print("="*40)
    print("🖥️  SYSTEM DIAGNOSTIC REPORT")
    print("="*40)

    # 1. OS & CPU Info
    print(f"[OS]       : {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"[CPU]      : {platform.processor()}")
    print(f"[Cores]    : Physical {psutil.cpu_count(logical=False)} / Logical {psutil.cpu_count(logical=True)}")
    
    # 2. RAM Info
    mem = psutil.virtual_memory()
    total_ram = round(mem.total / (1024**3), 2)
    avail_ram = round(mem.available / (1024**3), 2)
    print(f"[RAM]      : Total {total_ram} GB (Available: {avail_ram} GB)")

    print("-" * 40)

    # 3. Python & Libraries
    print(f"[Python]   : {sys.version.split()[0]}")
    print(f"[PyTorch]  : {torch.__version__}")
    
    try:
        import unsloth
        print(f"[Unsloth]  : Installed")
    except ImportError:
        print(f"[Unsloth]  : Not Installed")

    print("-" * 40)

    # 4. GPU Info (핵심)
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        print(f"[CUDA]     : Available (Version {torch.version.cuda})")
        print(f"[GPU Count]: {gpu_count}")
        
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            # VRAM 계산
            vram_total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            vram_allocated = torch.cuda.memory_allocated(i) / (1024**3)
            vram_reserved = torch.cuda.memory_reserved(i) / (1024**3)
            
            print(f"  Start -> GPU {i}: {gpu_name}")
            print(f"    - Total VRAM : {vram_total:.2f} GB")
            print(f"    - Used (PyTorch): {vram_allocated:.2f} GB")
            print(f"    - Reserved (Cache): {vram_reserved:.2f} GB")
    else:
        print("❌ [CUDA]     : Not Available (CPU only)")

    print("="*40)

if __name__ == "__main__":
    print_info()